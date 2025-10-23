import re
from models.models import User
from initdb import SessionLocal
from urllib.parse import urlparse, urljoin
from werkzeug.security import check_password_hash
from flask import Blueprint, render_template, request, redirect, url_for, session

auth = Blueprint("auth", __name__)


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    phone = re.sub(r"[^\d+]", "", phone.strip())
    if phone.startswith("0") and len(phone) >= 10:
        phone = "+38" + phone
    if re.fullmatch(r"\d{10}", phone):
        phone = "+38" + phone
    if phone and not phone.startswith("+"):
        phone = "+" + phone
    return phone


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@auth.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("profile"))

    error = None
    if request.method == "POST":
        identifier = (request.form.get("identifier") or "").strip()
        password = request.form.get("password", "")
        norm_phone = normalize_phone(identifier)

        db = SessionLocal()
        try:
            user = None
            if "@" in identifier:
                user = db.query(User).filter(User.email == identifier).first()
            else:
                user = db.query(User).filter(User.phone == norm_phone).first()
                if not user:
                    user = db.query(User).filter(User.phone == identifier).first()
            if not user:
                user = db.query(User).filter(User.username == identifier).first()

            if not user:
                error = "Користувача не знайдено. Перевірте email або телефон."
                return render_template("login.html", error=error)

            if not check_password_hash(user.hashed_password, password):
                error = "Неправильний логін або пароль."
                return render_template("login.html", error=error)

            session["user_id"] = user.id
            remember = request.form.get("remember")
            session.permanent = bool(remember)

            next_url = request.args.get("next")
            if next_url and is_safe_url(next_url):
                return redirect(next_url)
            return redirect(url_for("profile"))

        finally:
            db.close()

    return render_template("login.html", error=error)
