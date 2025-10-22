from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from models.models import User
from initdb import SessionLocal  # Импортируйте вашу функцию получения сессии БД
import re

reg_bp = Blueprint("reg", __name__, template_folder="../templates")


def validate_phone(phone):
    """Валидация номера телефона"""
    # Удаляем все нецифровые символы

    digits_only = re.sub(r"\D", "", phone)
    # Проверяем, что осталось минимум 10 цифр
    return len(digits_only) >= 10


def validate_email(email):
    """Валидация email"""
    if not email:  # email опциональный
        return True
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password(password):
    """Валидация пароля"""
    if len(password) < 8:
        return False, "Пароль повинен містити мінімум 8 символів"
    if not re.search(r"[A-Z]", password):
        return False, "Пароль повинен містити хоча б одну велику літеру"
    if not re.search(r"[a-z]", password):
        return False, "Пароль повинен містити хоча б одну малу літеру"
    if not re.search(r"[0-9]", password):
        return False, "Пароль повинен містити хоча б одну цифру"
    return True, ""


@reg_bp.route("/register")
def register():
    return render_template("register.html")


@reg_bp.route("/register-data", methods=["POST"])
def register_data():
    """Обработка данных регистрации"""

    # Получаем данные из формы
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "")
    password2 = request.form.get("password2", "")
    terms = request.form.get("terms")

    # Валидация на стороне сервера
    errors = []

    # Проверка полного имени
    if not full_name or len(full_name) < 2:
        errors.append("Повне ім'я повинно містити мінімум 2 символи")

    # Проверка email (если указан)
    if email and not validate_email(email):
        errors.append("Некоректна електронна адреса")

    # Проверка телефона
    if not phone:
        errors.append("Телефон обов'язковий")
    elif not validate_phone(phone):
        errors.append("Некоректний номер телефону")

    # Проверка пароля
    if not password:
        errors.append("Пароль обов'язковий")
    else:
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            errors.append(error_msg)

    # Проверка совпадения паролей
    if password != password2:
        errors.append("Паролі не співпадають")

    # Проверка согласия с условиями
    if not terms:
        errors.append("Ви повинні погодитись з умовами")

    # Если есть ошибки - возвращаем с сообщением
    if errors:
        print("Registration validation failed:", errors, flush=True)
        return render_template("register.html", error="; ".join(errors))

    # Работа с базой данных
    session = SessionLocal()

    try:
        # Проверяем, существует ли пользователь с таким телефоном
        existing_user = (
            session.query(User)
            .filter((User.phone == phone) | (User.username == full_name))
            .first()
        )

        if existing_user:
            if existing_user.phone == phone:
                error_msg = "Користувач з таким номером телефону вже існує"
            else:
                error_msg = "Користувач з таким ім'ям вже існує"

            print(f"Registration failed: {error_msg}", flush=True)
            return render_template("register.html", error=error_msg)

        # Если email указан, проверяем его уникальность
        if email:
            existing_email = session.query(User).filter(User.email == email).first()
            if existing_email:
                print("Registration failed: email already exists", flush=True)
                return render_template(
                    "register.html",
                    error="Користувач з такою електронною адресою вже існує",
                )

        # Создаем нового пользователя
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        new_user = User(
            username=full_name,
            phone=phone,
            email=email if email else None,
            hashed_password=hashed_password,
        )

        session.add(new_user)
        session.commit()

        print(f"New user registered successfully: {full_name} ({phone})", flush=True)

        # Устанавливаем flash-сообщение об успехе
        flash("Реєстрація успішна! Тепер ви можете увійти.", "success")

        # Перенаправляем на страницу входа или главную
        return redirect(url_for("login"))  # или url_for("index")

    except IntegrityError as e:
        session.rollback()
        print(f"Database integrity error: {e}", flush=True)
        return render_template(
            "register.html", error="Помилка реєстрації. Такий користувач вже існує."
        )

    except Exception as e:
        session.rollback()
        print(f"Registration error: {e}", flush=True)
        return render_template(
            "register.html", error="Виникла помилка при реєстрації. Спробуйте пізніше."
        )

    finally:
        session.close()
