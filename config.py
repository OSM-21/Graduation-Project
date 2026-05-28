# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================
# Security / Flask
# ============================
SECRET_KEY = os.environ.get("CHATBOT_SECRET", "change-this-secret")

# ============================
# Database
# ============================
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'chatbot.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ============================
# Paths / Data
# ============================
VECTORIZER_PATH = os.path.join(BASE_DIR, "data", "models", "vectorizer.pkl")
TFIDF_MATRIX_PATH = os.path.join(BASE_DIR, "data", "models", "tfidf_matrix.pkl")
EMBEDDINGS_PATH = os.path.join(BASE_DIR, "data", "models", "embeddings.pkl")

QA_JSON_PATH = os.path.join(BASE_DIR, "data", "questions_answers.json")
INTENTS_JSON_PATH = os.path.join(BASE_DIR, "data", "intents.json")
UNKNOWN_TXT_PATH = os.path.join(BASE_DIR, "data", "unknown_questions.txt")

# ============================
# Chatbot Settings (Local Only)
# ============================
# Similarity thresholds
CONFIDENCE_THRESHOLD = 0.75
LOW_CONFIDENCE_THRESHOLD = 0.55

# Hybrid scoring weights (SentenceTransformer + Char-TFIDF)
WEIGHT_ST = 0.80
WEIGHT_CHAR = 0.20

# ============================
# Email Settings (Password Reset)
# ============================
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False  # لازم False إذا TLS = True

MAIL_USERNAME = '202200231@stu.jazanu.edu.sa'
MAIL_PASSWORD = 'كلمة_مرور_التطبيق_الـ_16_حرفاً'  # ضع App Password الحقيقي هنا
MAIL_DEFAULT_SENDER = '202200231@stu.jazanu.edu.sa'

# ✅ أثناء التطوير: يمنع محاولة الإرسال ويمنع أخطاء "حصل خطأ"
MAIL_SUPPRESS_SEND = True
CHATBOT_DEBUG = True
CONFIDENCE_THRESHOLD = 0.60
WEIGHT_ST = 0.75
WEIGHT_CHAR = 0.25
LEXICAL_BOOST = 0.18
CHATBOT_DEBUG = False
