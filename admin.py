# admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash  # type: ignore
from flask_login import current_user  # type: ignore
from sqlalchemy import func  # type: ignore

from .models import QA, UnknownQuestion, Chat, User, Conversation
from .db import db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def require_admin():
    return (
        current_user.is_authenticated
        and current_user.role
        and current_user.role.name in ("Admin", "Editor")
    )


@admin_bp.before_request
def protect():
    open_paths = {"/admin/unauthorized"}
    if request.path in open_paths:
        return
    if not require_admin():
        return redirect(url_for("admin.unauthorized"))


@admin_bp.route("/unauthorized")
def unauthorized():
    return "غير مصرح بالدخول. اطلب من الأدمن منحك صلاحية.", 403


@admin_bp.route("/")
def dashboard():
    # عدد المستخدمين
    total_users = db.session.query(func.count(User.id)).scalar() or 0

    # ✅ عدد التقييمات (صح) من Conversation.rating
    pos = (
        db.session.query(func.count(Conversation.id))
        .filter(Conversation.rating == 1)
        .scalar()
        or 0
    )
    neg = (
        db.session.query(func.count(Conversation.id))
        .filter(Conversation.rating == -1)
        .scalar()
        or 0
    )

    # الأسئلة الأكثر تكرارًا (من Chat logs)
    top_questions = (
        db.session.query(Chat.question, func.count(Chat.id).label("cnt"))
        .group_by(Chat.question)
        .order_by(func.count(Chat.id).desc())
        .limit(10)
        .all()
    )

    # إجمالي الرسائل (Chat table)
    total_chats = db.session.query(func.count(Chat.id)).scalar() or 0

    # جلب بيانات المستخدمين
    users = User.query.all()
    user_stats = []

    for u in users:
        convs = Conversation.query.filter_by(user_id=u.id).all()

        total_conv = len(convs)
        pos_count = sum(1 for c in convs if c.rating == 1)
        neg_count = sum(1 for c in convs if c.rating == -1)
        total_rating = pos_count - neg_count

        user_stats.append(
            {
                "email": u.email,
                "role": u.role.name if u.role else "—",
                # ✅ لا نعرض الإجابات المشفرة/ولا عندنا security_q واحد أصلاً
                "security_q": "—",
                "security_a": "—",
                "total_conv": total_conv,
                "pos": pos_count,
                "neg": neg_count,
                "total_rating": total_rating,
            }
        )

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        pos=pos,
        neg=neg,
        total_chats=total_chats,
        top_questions=top_questions,
        users=user_stats,
    )


@admin_bp.route("/qa", methods=["GET", "POST"])
def qa():
    if request.method == "POST":
        q = request.form.get("question")
        a = request.form.get("answer")
        intent = request.form.get("intent")
        if q and a:
            if not QA.query.filter_by(question=q).first():
                db.session.add(QA(question=q, answer=a, intent=intent))
                db.session.commit()
                flash("تمت إضافة السؤال/الجواب", "success")
            else:
                flash("السؤال موجود مسبقًا", "warning")
        return redirect(url_for("admin.qa"))

    items = QA.query.order_by(QA.updated_at.desc()).all()
    return render_template("admin_qa.html", items=items)


@admin_bp.route("/qa/<int:item_id>/delete", methods=["POST"])
def delete_qa(item_id):
    item = QA.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("تم الحذف", "info")
    return redirect(url_for("admin.qa"))


@admin_bp.route("/unknown", methods=["GET", "POST"])
def unknown():
    import json, os

    if request.method == "POST":
        text = request.form.get("text")
        answer = request.form.get("answer")
        intent = request.form.get("intent")
        uid = request.form.get("uid")

        if text and answer:
            json_path = os.path.join("data", "questions_answers.json")

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    qa_list = json.load(f)
            except Exception:
                qa_list = []

            # ✅ عندك question في JSON غالباً list، فنتأكد بشكل مرن
            def is_same_question(item, qtext: str) -> bool:
                q = item.get("question")
                if isinstance(q, list):
                    return any(str(x).strip() == qtext.strip() for x in q)
                return str(q).strip() == qtext.strip()

            exists = any(is_same_question(item, text) for item in qa_list)

            if not exists:
                qa_list.append(
                    {
                        "question": text,
                        "answer": answer,
                        "intent": intent or "",
                    }
                )
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(qa_list, f, ensure_ascii=False, indent=4)

            unk = UnknownQuestion.query.get(uid)
            if unk:
                db.session.delete(unk)

            db.session.commit()
            flash("تم تحويل السؤال وإضافته للـ JSON بنجاح ✔", "success")

        return redirect(url_for("admin.unknown"))

    items = UnknownQuestion.query.order_by(UnknownQuestion.created_at.desc()).all()
    return render_template("admin_unknown.html", items=items)


@admin_bp.route("/stats")
def stats():
    top = (
        db.session.query(Chat.question, func.count(Chat.id).label("cnt"))
        .group_by(Chat.question)
        .order_by(func.count(Chat.id).desc())
        .limit(20)
        .all()
    )
    users = db.session.query(func.count(User.id)).scalar() or 0

    # ✅ التقييمات من Conversation (صح)
    pos = (
        db.session.query(func.count(Conversation.id))
        .filter(Conversation.rating == 1)
        .scalar()
        or 0
    )
    neg = (
        db.session.query(func.count(Conversation.id))
        .filter(Conversation.rating == -1)
        .scalar()
        or 0
    )

    return render_template("stats.html", top=top, users=users, pos=pos, neg=neg)


@admin_bp.route("/users")
def users():
    users = User.query.all()
    user_stats = []

    for u in users:
        convs = Conversation.query.filter_by(user_id=u.id).all()

        pos = sum(1 for c in convs if c.rating == 1)
        neg = sum(1 for c in convs if c.rating == -1)

        user_stats.append(
            {
                "id": u.id,
                "email": u.email,
                "role": u.role.name if u.role else "User",
                "last_login": u.last_login,
                "conv_count": len(convs),
                "pos": pos,
                "neg": neg,
                "score": pos - neg,
            }
        )

    return render_template("admin_users.html", users=user_stats)


@admin_bp.route("/users/<int:uid>")
def user_details(uid):
    user = User.query.get_or_404(uid)
    convs = (
        Conversation.query.filter_by(user_id=uid)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return render_template("admin_user_details.html", user=user, conversations=convs)


# ✅ راوت الأدمن لعرض محادثة كاملة
@admin_bp.route("/conversations/<int:cid>")
def conversation_details(cid):
    conv = Conversation.query.get_or_404(cid)

    messages = []
    try:
        # لو عندك علاقة conv.messages
        messages = sorted(conv.messages, key=lambda x: x.created_at)
    except Exception:
        messages = []

    return render_template("admin_conversation.html", conv=conv, messages=messages)


@admin_bp.route("/users/<int:uid>/delete", methods=["POST"])
def delete_user(uid):
    user = User.query.get_or_404(uid)

    # حذف محادثاته + رسائلها (لو ChatMessage موجود)
    convs = Conversation.query.filter_by(user_id=uid).all()
    for c in convs:
        try:
            from .models import ChatMessage  # type: ignore

            ChatMessage.query.filter_by(conversation_id=c.id).delete()
        except Exception:
            pass
        db.session.delete(c)

    # حذف سجل الشات
    Chat.query.filter_by(user_id=uid).delete()

    db.session.delete(user)
    db.session.commit()
    flash("تم حذف المستخدم", "info")
    return redirect(url_for("admin.users"))
