import traceback
from flask import Blueprint, render_template, request, jsonify, send_file, session
from flask_login import login_required, current_user
from io import BytesIO
from gtts import gTTS

from .chatbot import ChatbotEngine
from .web_api import RAGEngine
from .models import Chat, UnknownQuestion, Conversation, ChatMessage
from .db import db
from .utils import generate_title_from_question

views_bp = Blueprint("views", __name__)

# ======================================================
#  GLOBAL ENGINE
# ======================================================
GLOBAL_ENGINE = None
GLOBAL_RAG = None

def get_engine():
    global GLOBAL_ENGINE
    if GLOBAL_ENGINE is None:
        GLOBAL_ENGINE = ChatbotEngine()
    return GLOBAL_ENGINE

def get_rag():
    global GLOBAL_RAG
    if GLOBAL_RAG is None:
        GLOBAL_RAG = RAGEngine()
    return GLOBAL_RAG


# ======================================================
#  الصفحة الرئيسية
# ======================================================
@views_bp.route("/")
def index():
    if session.get("guest", False) or not current_user.is_authenticated:
        return render_template(
            "index.html",
            user=None,
            conversations=[],
            active_conv=None,
            guest=True
        )

    conversations = (
        Conversation.query
        .filter_by(user_id=current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    active_conv = conversations[0] if conversations else None

    return render_template(
        "index.html",
        user=current_user,
        conversations=conversations,
        active_conv=active_conv,
        guest=False
    )


# ======================================================
#  إرسال رسالة
# ======================================================
@views_bp.route("/chat", methods=["POST"])
def chat():
    rag = get_rag()
    is_guest = session.get("guest", False) or not current_user.is_authenticated

    data = request.get_json() or {}
    text = (data.get("text") or "").strip()
    conv_id = data.get("conversation_id")

    if not text:
        return jsonify({"answer": "اكتب سؤالك لو سمحت 🙂", "score": 0.0})

    try:
        result = rag.chat(conversation_id=str(conv_id or "default"), message=text)
        answer = result.get("answer", "") or "ما تم توليد رد."
        score = float(result.get("score", 0.0))
        debug_info = result.get("debug", {})

        print("\n" + "=" * 60)
        print("DEBUG /chat")
        print("User question:", text)
        print("Score:", score)
        print("Debug:", debug_info)
        print("=" * 60 + "\n")

    except Exception:
        print("\n" + "=" * 60)
        print("❌ ERROR in /chat (RAG)")
        traceback.print_exc()
        print("=" * 60 + "\n")
        return jsonify({
            "answer": "حصل خطأ داخلي في السيرفر. شوف التيرمنال لمعرفة السبب.",
            "score": 0.0,
            "conversation_id": "",
            "title": ""
        }), 500

    # زائر بدون حفظ
    if is_guest:
        return jsonify({
            "answer": answer,
            "score": score,
            "conversation_id": "",
            "title": ""
        })

    # مستخدم مسجل — حفظ
    conversation = None

    if conv_id:
        conversation = Conversation.query.filter_by(
            id=conv_id,
            user_id=current_user.id
        ).first()

    if conversation is None:
        title = generate_title_from_question(text)
        conversation = Conversation(user_id=current_user.id, title=title)
        db.session.add(conversation)
        db.session.flush()
    else:
        if not conversation.title or conversation.title == "محادثة جديدة":
            conversation.title = generate_title_from_question(text)

    # رسالة المستخدم
    db.session.add(ChatMessage(
        conversation_id=conversation.id,
        sender="user",
        text=text
    ))

    # رسالة البوت
    db.session.add(ChatMessage(
        conversation_id=conversation.id,
        sender="bot",
        text=answer
    ))

    # سجل الأدمن
    db.session.add(Chat(
        user_id=current_user.id,
        question=text,
        answer=answer
    ))

    # حفظ الأسئلة منخفضة الثقة
    try:
        if score < 0.75:
            db.session.add(UnknownQuestion(text=text))
    except Exception:
        pass

    db.session.commit()

    return jsonify({
        "answer": answer,
        "score": score,
        "conversation_id": conversation.id,
        "title": conversation.title
    })


# ======================================================
#  جلب محادثة
# ======================================================
@views_bp.route("/conversation/<int:cid>")
@login_required
def get_conversation(cid):
    conv = Conversation.query.filter_by(
        id=cid,
        user_id=current_user.id
    ).first_or_404()

    msgs = sorted(conv.messages, key=lambda m: m.created_at)
    messages = [{
        "sender": m.sender,
        "text": m.text,
        "created_at": m.created_at.isoformat()
    } for m in msgs]

    return jsonify({
        "id": conv.id,
        "title": conv.title,
        "messages": messages
    })


# ======================================================
#  إنشاء محادثة جديدة
# ======================================================
@views_bp.route("/conversation/new", methods=["POST"])
@login_required
def new_conversation():
    from datetime import datetime
    conv = Conversation(
        user_id=current_user.id,
        title="محادثة جديدة",
        created_at=datetime.utcnow()
    )
    db.session.add(conv)
    db.session.commit()

    return jsonify({
        "conversation_id": conv.id,
        "title": conv.title
    })


# ======================================================
#  تحويل الرد إلى صوت
# ======================================================
@views_bp.route("/tts", methods=["POST"])
def tts():
    text = (request.get_json() or {}).get("text", "")
    if not text:
        return jsonify({"error": "empty"}), 400

    mp3 = BytesIO()
    gTTS(text=text, lang="ar").write_to_fp(mp3)
    mp3.seek(0)
    return send_file(mp3, mimetype="audio/mpeg")


# ======================================================
#  تقييم المحادثة
# ======================================================
@views_bp.route("/rate_conversation", methods=["POST"])
@login_required
def rate_conversation():
    data = request.get_json() or {}
    conv_id = data.get("conversation_id")
    value = data.get("value")

    conv = Conversation.query.filter_by(
        id=conv_id,
        user_id=current_user.id
    ).first()

    if not conv:
        return jsonify({"ok": False}), 400

    if conv.rating is not None:
        return jsonify({"ok": True, "message": "already rated"})

    conv.rating = value
    db.session.commit()
    return jsonify({"ok": True})


# ======================================================
#  حذف محادثة
# ======================================================
@views_bp.route("/conversation/<int:cid>/delete", methods=["POST"])
@login_required
def delete_conversation(cid):
    conv = Conversation.query.filter_by(
        id=cid,
        user_id=current_user.id
    ).first()

    if not conv:
        return jsonify({"ok": False}), 404

    # حذف الرسائل المرتبطة
    ChatMessage.query.filter_by(conversation_id=cid).delete()

    # حذف المحادثة
    db.session.delete(conv)
    db.session.commit()

    return jsonify({"ok": True})