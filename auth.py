# auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from passlib.hash import bcrypt
from datetime import datetime

from .db import db
from .models import User, Role

auth_bp = Blueprint("auth", __name__)

# ============================
# Login
# ============================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if not user or not bcrypt.verify(password, user.password_hash):
            flash("بيانات الدخول غير صحيحة.", "error")
            return render_template("login.html")

        # ✅ تحديث آخر دخول
        user.last_login = datetime.utcnow()
        db.session.commit()

        # ✅ امسح وضع الزائر لو كان مفعّل
        session.pop("guest", None)

        login_user(user)

        # ✅ (اختياري) لو تبغى الأدمن يروح لوحة الأدمن
        try:
            if user.role and user.role.name == "Admin":
                return redirect(url_for("admin.dashboard"))
        except Exception:
            pass

        return redirect(url_for("views.index"))

    return render_template("login.html")


# ============================
# Register (مع 3 أسئلة)
# ============================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        q1 = (request.form.get("q1") or "").strip()
        a1 = (request.form.get("a1") or "").strip()
        q2 = (request.form.get("q2") or "").strip()
        a2 = (request.form.get("a2") or "").strip()
        q3 = (request.form.get("q3") or "").strip()
        a3 = (request.form.get("a3") or "").strip()

        if not email or not password:
            flash("اكتب البريد وكلمة المرور.", "error")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("هذا البريد مسجل مسبقًا.", "error")
            return render_template("register.html")

        if not (q1 and a1 and q2 and a2 and q3 and a3):
            flash("لازم تعبّي 3 أسئلة أمان مع الإجابات.", "error")
            return render_template("register.html")

        user_role = Role.query.filter_by(name="User").first()
        if not user_role:
            user_role = Role(name="User")
            db.session.add(user_role)
            db.session.commit()

        u = User(
            email=email,
            password_hash=bcrypt.hash(password),
            role=user_role,
            security_q1=q1,
            security_a1=bcrypt.hash(a1),
            security_q2=q2,
            security_a2=bcrypt.hash(a2),
            security_q3=q3,
            security_a3=bcrypt.hash(a3),
        )
        db.session.add(u)
        db.session.commit()

        flash("تم إنشاء الحساب. سجل دخول الآن.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ============================
# Guest Login
# ============================
@auth_bp.route("/guest-login")
def guest_login():
    # ✅ لو كان مسجل دخول بحساب، طلّعه أول
    if current_user.is_authenticated:
        logout_user()

    session["guest"] = True
    return redirect(url_for("views.index"))


# ============================
# Logout
# ============================
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()

    # ✅ امسح وضع الزائر احتياط
    session.pop("guest", None)

    return redirect(url_for("auth.login"))


# ==========================================================
# Forgot Password Flow (3 steps)
# ==========================================================

# 1) صفحة: أدخل البريد
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("ما لقينا حساب بهذا البريد.", "error")
            return render_template("forgot_password.html")

        session["reset_user_id"] = user.id
        return redirect(url_for("auth.security_questions"))

    return render_template("forgot_password.html")


# 2) صفحة: الأسئلة الثلاثة
@auth_bp.route("/security-questions", methods=["GET", "POST"])
def security_questions():
    uid = session.get("reset_user_id")
    if not uid:
        return redirect(url_for("auth.forgot_password"))

    user = User.query.get(uid)
    if not user:
        session.pop("reset_user_id", None)
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        a1 = (request.form.get("a1") or "").strip()
        a2 = (request.form.get("a2") or "").strip()
        a3 = (request.form.get("a3") or "").strip()

        ok = True
        try:
            ok = ok and bcrypt.verify(a1, user.security_a1 or "")
            ok = ok and bcrypt.verify(a2, user.security_a2 or "")
            ok = ok and bcrypt.verify(a3, user.security_a3 or "")
        except Exception:
            ok = False

        if not ok:
            flash("إجابات الأمان غير صحيحة.", "error")
            return render_template(
                "security_questions.html",
                q1=user.security_q1,
                q2=user.security_q2,
                q3=user.security_q3
            )

        session["reset_verified"] = True
        return redirect(url_for("auth.reset_password"))

    return render_template(
        "security_questions.html",
        q1=user.security_q1,
        q2=user.security_q2,
        q3=user.security_q3
    )


# 3) صفحة: كلمة المرور الجديدة
@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    uid = session.get("reset_user_id")
    verified = session.get("reset_verified", False)

    if not uid or not verified:
        return redirect(url_for("auth.forgot_password"))

    user = User.query.get(uid)
    if not user:
        session.pop("reset_user_id", None)
        session.pop("reset_verified", None)
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        p1 = request.form.get("password") or ""
        p2 = (request.form.get("confirm_password") or "")

        if len(p1) < 6:
            flash("كلمة المرور لازم تكون 6 أحرف أو أكثر.", "error")
            return render_template("reset_password.html")

        if p1 != p2:
            flash("كلمتا المرور غير متطابقتين.", "error")
            return render_template("reset_password.html")

        user.password_hash = bcrypt.hash(p1)
        db.session.commit()

        session.pop("reset_user_id", None)
        session.pop("reset_verified", None)

        flash("تم تغيير كلمة المرور. سجل دخول الآن.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")
