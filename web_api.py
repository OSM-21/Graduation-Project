import os
import json
import re
import time
from pathlib import Path
from groq import Groq


class RAGEngine:
    def __init__(
        self,
        groq_model="llama-3.1-8b-instant",
    ):
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        self.QA_JSON_PATH = self.BASE_DIR / "data" / "questions_answers_clean.json"
        self.GROQ_MODEL = groq_model

        self.stopwords = {
            "كم", "كيف", "هل", "متى", "وين", "ايش", "وش", "ما", "هو", "هي",
            "على", "في", "من", "عن", "الى", "إلى", "او", "أو", "اذا", "إذا",
            "اقدر", "يمكن", "ابغى", "اريد", "ابي", "لو", "عندي",
            "يعني", "مثلا", "بس", "طيب", "الحين", "هذا", "هذه", "ذا", "ذي"
        }

        self.intent_keywords = {
            "scholarship": {
                "مكافاه", "مكافاة", "مكافآت", "مكافات", "المكافاه", "المكافاة", "المكافات"
            },
            "absence": {
                "غياب", "الغياب", "حضور", "نسبه", "النسبه", "حرمان"
            },
            "housing": {
                "سكن", "السكن", "سكني", "السكني"
            },
            "registration": {
                "تسجيل", "اسجل", "اضافه", "إضافة", "حذف", "انسحاب", "تسجيلي"
            },
            "schedule": {
                "جدول", "الجداول", "شعبه", "شعبة", "محاضره", "محاضرة", "قاعه", "قاعة"
            },
            "blackboard": {
                "بلاكبورد", "blackboard", "lms"
            },
            "library": {
                "مكتبه", "مكتبة", "كتاب", "كتب", "استعاره", "استعارة"
            },
            "university_app": {
                "تطبيق", "ابلكيشن", "application", "app"
            },
            "systems_access": {
                "انظمه", "أنظمة", "النظام", "الانظمة", "دخول", "ادخل", "اخش", "الصيانه", "صيانة", "اجازه", "إجازة"
            },

              "allowed_absence": {
        "غياب", "الغياب", "نسبه", "النسبه", "مسموح", "المسموح", "حرمان"
    },

    "exceed_absence": {
        "تجاوز", "تعديت", "حرمان", "غياب", "النسبه", "الغياب"
    },

    "dorm_available": {
        "سكن", "السكن", "سكني", "السكني"
    },

    "change_section_during_add_drop": {
        "شعبه", "شعبة", "تغيير", "تبديل"
    },

    "course_conflict_meaning": {
        "تعارض", "جدول", "يتعارض", "تداخل"
    },

    "blackboard_account": {
        "بلاكبورد", "blackboard"
    },

    "library_location": {
        "مكتبه", "مكتبة", "موقع", "وين"
    },

    "printing_options": {
        "طباعه", "طباعة", "اطبع"
    },
        }

        self._load_qa()
        self._load_groq()

    # =========================
    # Helpers
    # =========================
    def normalize_ar(self, text: str) -> str:
        if not text:
            return ""
        t = text.strip().lower()
        t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        t = t.replace("ى", "ي")
        t = t.replace("ة", "ه")
        t = t.replace("ؤ", "و")
        t = t.replace("ئ", "ي")
        t = t.replace("ـ", "")
        t = re.sub(r"[^\w\s\u0600-\u06FF]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def tokenize(self, text: str):
        return [w for w in self.normalize_ar(text).split() if w]

    def important_tokens(self, text: str):
        return [w for w in self.tokenize(text) if w not in self.stopwords]

    # =========================
    # Load QA
    # =========================
    def _load_qa(self):
        if not self.QA_JSON_PATH.exists():
            raise FileNotFoundError(f"Missing {self.QA_JSON_PATH}")

        with open(self.QA_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise RuntimeError("questions_answers_clean.json لازم يكون list")

        self.qa_data = data
        self.intent_map = {}

        for item in self.qa_data:
            intent = str(item.get("intent", "")).strip()
            if not intent:
                continue

            questions = item.get("questions")
            if questions is None:
                questions = item.get("question", [])
            questions = questions or []

            answers = item.get("answers")
            if answers is None:
                single = item.get("answer", "")
                answers = [single] if str(single).strip() else []
            answers = [str(a).strip() for a in answers if str(a).strip()]

            tags = item.get("tags", []) or []

            if intent not in self.intent_map:
                self.intent_map[intent] = {
                    "questions": [],
                    "answers": [],
                    "tags": set(),
                }

            self.intent_map[intent]["questions"].extend(
                [str(q).strip() for q in questions if str(q).strip()]
            )
            self.intent_map[intent]["answers"].extend(answers)

            for tag in tags:
                tag = str(tag).strip()
                if tag:
                    self.intent_map[intent]["tags"].add(tag)

        for intent in self.intent_map:
            self.intent_map[intent]["questions"] = list(dict.fromkeys(self.intent_map[intent]["questions"]))
            self.intent_map[intent]["answers"] = list(dict.fromkeys(self.intent_map[intent]["answers"]))
            self.intent_map[intent]["tags"] = sorted(list(self.intent_map[intent]["tags"]))

    # =========================
    # Load Groq
    # =========================
    def _load_groq(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GROQ_API_KEY")
        self.groq_client = Groq(api_key=api_key)

    # =========================
    # Intent detection
    # =========================
    def keyword_intent_scores(self, user_q: str):
        tokens = set(self.important_tokens(user_q))
        scores = {}

        for intent, words in self.intent_keywords.items():
            match_count = len(tokens & words)
            if match_count > 0:
                scores[intent] = float(match_count)

        return scores

    def question_overlap_score(self, user_q: str, intent: str):
        info = self.intent_map.get(intent)
        if not info:
            return 0.0

        user_tokens = set(self.important_tokens(user_q))
        if not user_tokens:
            return 0.0

        best = 0.0
        for q in info["questions"]:
            q_tokens = set(self.important_tokens(q))
            if not q_tokens:
                continue
            score = len(user_tokens & q_tokens) / max(1, len(user_tokens))
            if score > best:
                best = score

        return best

    def choose_intent(self, user_q: str):
        candidate_scores = {}

        kw_scores = self.keyword_intent_scores(user_q)
        for intent, s in kw_scores.items():
            candidate_scores[intent] = candidate_scores.get(intent, 0.0) + (2.0 * s)

        for intent in self.intent_map.keys():
            overlap = self.question_overlap_score(user_q, intent)
            if overlap > 0:
                candidate_scores[intent] = candidate_scores.get(intent, 0.0) + overlap

        if not candidate_scores:
            return None, {"mode": "no_intent"}

        ranked = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        chosen_intent, chosen_score = ranked[0]

        return chosen_intent, {
            "mode": "intent_keyword_first",
            "chosen_intent": chosen_intent,
            "intent_score": chosen_score,
            "top_candidates": ranked[:5]
        }

    # =========================
    # Context building
    # =========================
    def build_context(self, intent: str):
        info = self.intent_map.get(intent)
        if not info:
            return None

        questions = [q for q in info.get("questions", []) if str(q).strip()]
        answers = [a for a in info.get("answers", []) if str(a).strip()]
        tags = info.get("tags", [])

        unique_questions = []
        seen_q = set()
        for q in questions:
            nq = self.normalize_ar(q)
            if nq not in seen_q:
                seen_q.add(nq)
                unique_questions.append(q)

        unique_answers = []
        seen_a = set()
        for a in answers:
            na = self.normalize_ar(a)
            if na not in seen_a:
                seen_a.add(na)
                unique_answers.append(a)

        return {
            "intent": intent,
            "questions": unique_questions[:8],
            "answers": unique_answers[:6],
            "tags": tags[:8]
        }

    # =========================
    # Groq formatting
    # =========================
    def groq_answer(self, user_q, context_data):
        examples_text = "\n".join([f"- {q}" for q in context_data["questions"] if q.strip()])
        answers_text = "\n".join([f"- {a}" for a in context_data["answers"] if a.strip()])
        tags_text = ", ".join(context_data["tags"])

        system = (
            "أنت مساعد جامعي لجامعة جازان.\n"
            "اكتب بالعربية فقط.\n"
            "مهمتك إعادة صياغة الإجابة اعتمادًا على المعرفة المعطاة فقط.\n"
            "ممنوع إضافة أي معلومة غير موجودة في المعرفة.\n"
            "لكن مسموح لك إعادة الترتيب والشرح والتوضيح والدمج بين الجمل المتاحة.\n"
            "لا تكتب اقتراحات.\n"
            "لا تكتب خيارات.\n"
            "لا تكتب سؤال متابعة.\n"
            "اكتب جوابًا بشريًا واضحًا ومرتبًا، وليس نسخة حرفية من النص.\n"
            "يفضل أن تكون الإجابة من فقرتين أو ثلاث فقرات قصيرة إذا كان ذلك مناسبًا."
        )

        user = f"""
سؤال الطالب:
{user_q}

الـ intent المختار:
{context_data["intent"]}

أمثلة أسئلة من نفس الموضوع:
{examples_text}

المعلومات المتاحة للإجابة:
{answers_text}

الوسوم:
{tags_text}

المطلوب:
- أعد صياغة جواب واضح ومفيد لنفس السؤال.
- لا تنسخ النص حرفيًا إذا أمكن.
- لا تضف أي معلومة من خارج البيانات.
- إذا كانت البيانات لا تكفي للإجابة المباشرة فاكتب فقط:
المعلومة غير متوفرة في قاعدة المعرفة.
"""

        resp = self.groq_client.chat.completions.create(
            model=self.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.35,
            max_tokens=420,
        )

        return resp.choices[0].message.content.strip()

    def safe_generate_answer(self, user_q, context_data):
        for attempt in range(2):
            try:
                return self.groq_answer(user_q, context_data), "groq"
            except Exception as e:
                print("\n" + "=" * 60)
                print(f"⚠️ Groq failed (attempt {attempt + 1})")
                print(repr(e))
                print("=" * 60 + "\n")
                time.sleep(1)

        return "⚠️ حصل خطأ في الاتصال بالذكاء الاصطناعي. حاول مرة ثانية.", "groq_failed"

    # =========================
    # Main chat
    # =========================
    def chat(self, conversation_id, message):
        message = (message or "").strip()

        if not message:
            return {
                "answer": "اكتب سؤالك لو سمحت 🙂",
                "score": 0.0,
                "options": [],
                "debug": {"mode": "empty"}
            }

        chosen_intent, intent_debug = self.choose_intent(message)

        if not chosen_intent:
            return {
                "answer": "المعلومة غير متوفرة في قاعدة المعرفة.",
                "score": 0.0,
                "options": [],
                "debug": intent_debug
            }

        context_data = self.build_context(chosen_intent)

        if not context_data or not context_data["answers"]:
            return {
                "answer": "المعلومة غير متوفرة في قاعدة المعرفة.",
                "score": 0.0,
                "options": [],
                "debug": {
                    **intent_debug,
                    "mode": "intent_without_answers"
                }
            }

        final_answer, answer_mode = self.safe_generate_answer(message, context_data)

        print("\n==============================")
        print("DEBUG")
        print("Question:", message)
        print("Chosen intent:", chosen_intent)
        print("Questions count:", len(context_data["questions"]))
        print("Answers count:", len(context_data["answers"]))
        print("Answer mode:", answer_mode)
        print("==============================\n")

        return {
            "answer": final_answer,
            "score": 1.0,
            "options": [],
            "debug": {
                **intent_debug,
                "answer_mode": answer_mode,
                "questions_count": len(context_data["questions"]),
                "answers_count": len(context_data["answers"])
            }
        }