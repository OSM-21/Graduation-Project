# models.py
from datetime import datetime
from flask_login import UserMixin
from .db import db

# ============================
#        Roles
# ============================
class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)


# ============================
#        Users
# ============================
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)

    # كلمة المرور
    password_hash = db.Column(db.String(255), nullable=False)

    # ✅ 3 أسئلة أمان + 3 إجابات
    security_q1 = db.Column(db.String(255), nullable=True)
    security_a1 = db.Column(db.String(255), nullable=True)

    security_q2 = db.Column(db.String(255), nullable=True)
    security_a2 = db.Column(db.String(255), nullable=True)

    security_q3 = db.Column(db.String(255), nullable=True)
    security_a3 = db.Column(db.String(255), nullable=True)

    # آخر تسجيل دخول
    last_login = db.Column(db.DateTime, nullable=True)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    role = db.relationship("Role")

    conversations = db.relationship("Conversation", backref="user", lazy=True)


# ============================
#        Conversations
# ============================
class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    title = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    rating = db.Column(db.Integer, nullable=True)  # 👍 = 1 ، 👎 = -1 ، None

    messages = db.relationship("ChatMessage", backref="conversation", lazy=True)


# ============================
#        Chat Messages
# ============================
class ChatMessage(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"))

    sender = db.Column(db.String(10))  # user / bot
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================
#     History (all chats)
# ============================
class Chat(db.Model):
    __tablename__ = "chat_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)

    question = db.Column(db.Text)
    answer = db.Column(db.Text)

    rating = db.Column(db.Integer, default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================
#    Unknown Questions
# ============================
class UnknownQuestion(db.Model):
    __tablename__ = "unknown_questions"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================
#     QA Dataset
# ============================
class QA(db.Model):
    __tablename__ = "qa"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, unique=True, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(100))

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
