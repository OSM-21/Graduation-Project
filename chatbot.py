# chatbot.py
import os
import json
import random
import hashlib
import pickle

from flask import current_app
from sentence_transformers import SentenceTransformer
import faiss

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .utils import normalize_view

EMBED_CACHE = "data/faiss_cache.pkl"


class ChatbotEngine:
    """
    ✅ Semantic retrieval (Sentence-Transformers) + FAISS
    ✅ Hybrid rerank: FAISS + CharTFIDF + Lexical overlap
    ✅ يقلل خلط المواضيع عبر:
        - TopK search
        - intent keyword hint (اختياري)
        - margin بين intents فقط (مو داخل نفس intent)
        - threshold ديناميكي للأسئلة القصيرة/العامة
    ✅ يدعم ملفات QA فيها:
        - "answers": [..]
        - أو "answer": "..."
    """

    def __init__(self):
        self.qa_path = current_app.config["QA_JSON_PATH"]

        # Thresholds (قيم عملية - تقدر ترفعها إذا تبغى تشدد)
        self.threshold = float(current_app.config.get("CONFIDENCE_THRESHOLD", 0.69))
        self.short_q_threshold = float(current_app.config.get("SHORT_Q_THRESHOLD", 0.69))
        self.short_q_words = int(current_app.config.get("SHORT_Q_WORDS", 4))
        self.generic_q_threshold = float(current_app.config.get("GENERIC_Q_THRESHOLD", 0.69))

        # margin: نستخدمه فقط إذا أفضل نتيجتين من intents مختلفة
        self.margin = float(current_app.config.get("CONFIDENCE_MARGIN", 0.015))

        # topK
        self.top_k = int(current_app.config.get("TOP_K", 20))

        # Hybrid weights
        self.w_faiss = float(current_app.config.get("W_FAISS", 0.68))
        self.w_char = float(current_app.config.get("W_CHAR", 0.22))
        self.w_lex = float(current_app.config.get("W_LEX", 0.10))

        # Debug
        self.debug = bool(current_app.config.get("CHATBOT_DEBUG", False))

        # ST model
        self.model = SentenceTransformer(
            current_app.config.get(
                "ST_MODEL_NAME",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
        )

        self.qa_data = self._load_qa()
        self._build_index()

        self._last_answer = {}

        # كلمات مفتاحية (اختياري)
        self.intent_keywords = {
            "university_app": ["تطبيق", "ابلكيشن", "app", "application"],
            "blackboard": ["بلاك", "blackboard", "lms"],
            "scholarship": ["مكاف", "مكافأة", "مكافات", "مكافآت"],
            "library": ["مكتبه", "مكتبة", "كتب", "استعاره", "استعارة", "طباعة"],
            "registration": ["تسجيل", "اسجل", "أسجل", "اضافه", "إضافة", "حذف", "سحب", "انسحاب"],
            "schedule": ["جدول", "شعبه", "شعبة", "قاعه", "قاعة", "تعارض"],
            "housing": ["سكن", "سكني", "سكن جامعي"],
        }

    # -----------------------
    def _load_qa(self):
        if not os.path.exists(self.qa_path):
            return []
        with open(self.qa_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # -----------------------
    def _hash_file(self, path):
        h = hashlib.md5()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    # -----------------------
    def _coerce_answers(self, item):
        """
        يدعم:
        - answers: [...]
        - answer: "..."
        """
        answers = item.get("answers", None)

        if answers is None:
            single = item.get("answer", "")
            answers = [single] if str(single).strip() else []
        elif not isinstance(answers, list):
            answers = [str(answers)]

        answers = [str(a).strip() for a in answers if str(a).strip()]
        return answers

    # -----------------------
    def _build_index(self):
        self.questions = []
        self.answer_pools = []
        self.intents = []

        for item in self.qa_data:
            qs = item.get("question", []) or []
            intent = item.get("intent", "general") or "general"
            answers = self._coerce_answers(item)

            if not answers:
                continue

            for q in qs:
                q = str(q).strip()
                if not q:
                    continue

                self.questions.append(normalize_view(q))
                self.answer_pools.append(answers)
                self.intents.append(intent)

        if not self.questions:
            self.index = None
            return

        # Char TFIDF (ممتاز للأخطاء الإملائية/الاختلافات البسيطة)
        self.char_vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1
        )
        self.char_X = self.char_vectorizer.fit_transform(
            [normalize_view(q, remove_stopwords=True) for q in self.questions]
        )

        file_key = self._hash_file(self.qa_path)

        # cache
        if os.path.exists(EMBED_CACHE):
            try:
                with open(EMBED_CACHE, "rb") as f:
                    cache = pickle.load(f)
                if cache.get("key") == file_key:
                    self.embeddings = cache["embeddings"]
                    self.index = cache["index"]
                    if self.debug:
                        print("✅ FAISS loaded from cache")
                    return
            except Exception:
                pass

        if self.debug:
            print("🧠 Building FAISS index...")

        self.embeddings = self.model.encode(
            self.questions, normalize_embeddings=True
        ).astype("float32")

        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(self.embeddings)

        os.makedirs("data", exist_ok=True)
        with open(EMBED_CACHE, "wb") as f:
            pickle.dump({"key": file_key, "embeddings": self.embeddings, "index": self.index}, f)

        if self.debug:
            print("💾 FAISS index saved")

    # -----------------------
    def _pick_answer(self, idx, user_key):
        pool = self.answer_pools[idx] if 0 <= idx < len(self.answer_pools) else []
        if not pool:
            return ""

        last = self._last_answer.get((idx, user_key))
        choices = list(range(len(pool)))

        if last in choices and len(choices) > 1:
            choices.remove(last)

        pick = random.choice(choices)
        self._last_answer[(idx, user_key)] = pick
        return pool[pick]

    # -----------------------
    def _dynamic_threshold(self, user_norm: str) -> float:
        wc = len(user_norm.split())
        th = self.threshold

        # قصير جدًا
        if wc <= self.short_q_words:
            th = max(th, self.short_q_threshold)

        # عام جدًا
        generic_words = {"فيه", "موجود", "هل", "يوجد", "عندكم", "عندكم؟", "عندكم"}
        tokens = set(user_norm.split())
        if len(tokens) <= 3 and (tokens & generic_words):
            th = max(th, self.generic_q_threshold)

        return th

    # -----------------------
    def _guess_intent_from_keywords(self, user_norm: str):
        hits = {}
        for intent, kws in self.intent_keywords.items():
            for kw in kws:
                if kw in user_norm:
                    hits[intent] = hits.get(intent, 0) + 1
        if not hits:
            return None
        return max(hits.items(), key=lambda x: x[1])[0]

    # -----------------------
    def answer(self, user_text):
        if not self.index:
            return "قاعدة المعرفة فارغة.", 0.0

        user_norm = normalize_view(user_text)
        vec = self.model.encode([user_norm], normalize_embeddings=True).astype("float32")

        k = max(5, int(self.top_k))
        scores, ids = self.index.search(vec, k)

        if ids is None or ids.size == 0:
            return "ما قدرت أحدد إجابة دقيقة لسؤالك.", 0.0

        # candidates
        candidates = []
        for s, i in zip(scores[0], ids[0]):
            i = int(i)
            s = float(s)
            if i < 0 or i >= len(self.intents):
                continue
            candidates.append((s, i))

        if not candidates:
            return "ما قدرت أحدد إجابة دقيقة لسؤالك.", 0.0

        # ===== Hybrid scores لكل المرشحين =====
        user_char = normalize_view(user_text, remove_stopwords=True)
        v_char = self.char_vectorizer.transform([user_char])
        char_scores = cosine_similarity(v_char, self.char_X).ravel()

        u_set = set(user_norm.split())

        reranked_all = []
        for faiss_s, qi in candidates:
            q = self.questions[qi]
            q_set = set(q.split())

            overlap = 0.0
            if u_set and q_set:
                overlap = len(u_set & q_set) / max(1, len(u_set))

            final = (self.w_faiss * faiss_s) + (self.w_char * float(char_scores[qi])) + (self.w_lex * overlap)
            reranked_all.append((final, float(faiss_s), qi, self.intents[qi]))

        reranked_all.sort(reverse=True, key=lambda x: x[0])
        best_final, best_faiss, best_idx, best_intent = reranked_all[0]

        # ===== margin فقط إذا التنافس من INTENT مختلفة =====
        second_diff_intent = None
        for item in reranked_all[1:]:
            if item[3] != best_intent:
                second_diff_intent = item
                break

        if second_diff_intent is not None:
            second_final = second_diff_intent[0]
            if (best_final - second_final) < self.margin:
                # بدال "سؤالك قريب..." نعطي أفضل جواب لكن نكون حذرين
                # (وهذا يخليك ما توقف المستخدم)
                if self.debug:
                    print(f"[DEBUG] margin hit: best={best_final:.3f} second_other_intent={second_final:.3f}")
                # نكمل ونرد بأفضل شيء بدل طلب توضيح

        # ===== intent target (keywords optional) =====
        guessed = self._guess_intent_from_keywords(user_norm)
        target_intent = guessed if guessed else best_intent

        # فلترة داخل target_intent
        filtered = [(final, faiss_s, qi) for (final, faiss_s, qi, it) in reranked_all if it == target_intent]

        # لو ما لقى داخل intent المتوقّع، رجع لأفضل intent
        if not filtered:
            target_intent = best_intent
            filtered = [(final, faiss_s, qi) for (final, faiss_s, qi, it) in reranked_all if it == target_intent]

        filtered.sort(reverse=True, key=lambda x: x[0])
        final_score, faiss_score, idx = filtered[0]

        # threshold ديناميكي
        th = self._dynamic_threshold(user_norm)
        if final_score < th:
            return "ما قدرت أحدد إجابة دقيقة لسؤالك، حاول تصيغه بطريقة ثانية.", float(final_score)

        if self.debug:
            print(
                f"[DEBUG] user='{user_text}' intent='{self.intents[idx]}' "
                f"final={final_score:.3f} faiss={faiss_score:.3f} match='{self.questions[idx]}'"
            )

        answer_text = self._pick_answer(idx, user_norm)
        return answer_text, float(final_score)