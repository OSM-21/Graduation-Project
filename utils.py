# utils.py
import os, re, json, shutil, datetime
from .models import Role, QA
from .db import db

# ==============================
# 1) دالة إنشاء البيانات الأساسية (أدوار + أدمن)
# ==============================
def ensure_seed_data():
    for name in ("Admin", "Editor", "User"):
        if not Role.query.filter_by(name=name).first():
            db.session.add(Role(name=name))
    db.session.commit()

    from .models import User
    from passlib.hash import bcrypt
    if not User.query.filter_by(email="admin@local").first():
        admin_role = Role.query.filter_by(name="Admin").first()
        user = User(email="admin@local", password_hash=bcrypt.hash("admin123"), role=admin_role)
        db.session.add(user)
        db.session.commit()

    qa_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "questions_answers.json")
    if not os.path.exists(qa_path):
        sample = [
            {"question": ["هل يوجد سكن جامعي؟"], "answer": "نعم، يوجد سكن جامعي للطالبات عبر عمادة شؤون الطالبات.", "intent": "housing"},
            {"question": ["متى تصرف المكافأة؟"], "answer": "تصرف عادة بنهاية كل شهر ميلادي — أي استفسار راجع الشؤون المالية.", "intent": "scholarship"},
            {"question": ["كيف أسجل المواد؟"], "answer": "من خلال بوابة الطالب — قسم التسجيل — إضافة مقررات.", "intent": "registration"},
        ]
        with open(qa_path, "w", encoding="utf-8") as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)


# ==============================
# 2) تنميط النص العربي (نظيف واحترافي)
# ==============================
_ARABIC_DIACRITICS = re.compile(r"[ًٌٍَُِّْـ]")
_ARABIC_LETTERS_NORM = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا",
    "ى": "ي",
    "ؤ": "و",
    "ئ": "ي",
    # "ة": "ه",  # ❌ خله معطل لتقليل الخلط
})

_STOPWORDS = set([
    "وش", "ايش", "اي", "ما", "هو", "هي", "وشو", "وشي", "ايش هو",
    "من", "الى", "على", "في", "عن", "مع", "هذا", "هذه", "ذا", "ذي",
    "كيف", "متى", "وين", "ليش", "هل", "كم", "ايش", "وش", "لو",
])

def normalize_arabic(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()

    # إزالة التشكيل
    t = _ARABIC_DIACRITICS.sub("", t)

    # تطبيع الحروف
    t = t.translate(_ARABIC_LETTERS_NORM)

    # إبقاء العربية/الأرقام/المسافات فقط + حروف لاتينية (علشان blackboard)
    t = re.sub(r"[^a-z0-9\u0600-\u06FF\s]", " ", t)

    # توحيد المسافات
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_view(text: str, remove_stopwords: bool = False) -> str:
    """
    View نظيف للنص:
    - normalize_arabic
    - (اختياري) إزالة كلمات عامة جدًا تساعد على فهم المعنى بدون ما تتسبب بتشويش
    """
    t = normalize_arabic(text)
    if not t:
        return ""

    if remove_stopwords:
        tokens = [w for w in t.split() if w not in _STOPWORDS]
        t = " ".join(tokens).strip()

    return t


# ==============================
# 3) عمل نسخة احتياطية للقاعدة
# ==============================
def create_backup():
    base = os.path.dirname(os.path.dirname(__file__))
    db_path = os.path.join(base, "chatbot.db")
    if os.path.exists(db_path):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backups = os.path.join(base, "backups")
        os.makedirs(backups, exist_ok=True)
        shutil.copy(db_path, os.path.join(backups, f"backup_{ts}.db"))


# ==============================
# 4) توليد عنوان مختصر وذكي للمحادثة (كما هو)
# ==============================
def generate_title_from_question(text):
    t = text.strip()
    t = re.sub(r"[^\u0600-\u06FF0-9\s]", "", t)
    t = t.replace("؟", "").strip()

    keywords = {
        "سكن": "السكن الجامعي",
        "مكاف": "المكافآت",
        "تسجيل": "التسجيل",
        "اسجل": "التسجيل",
        "جدول": "الجداول الدراسية",
        "تحويل": "التحويل الأكاديمي",
        "معدل": "المعدل",
        "منحة": "المنح",
        "منح": "المنح",
    }

    for k, v in keywords.items():
        if k in t:
            return v

    words = t.split()
    if len(words) >= 2:
        return " ".join(words[:2])
    elif len(words) == 1:
        return words[0]
    return "محادثة"
