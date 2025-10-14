import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from werkzeug.utils import secure_filename

from initdb import SessionLocal, init_db, engine
from models.models import (
    Category,
    Product,
    ProductImage,
)  # models.py должен содержать класс Category

app = Flask(__name__)
app.secret_key = "Lql8aLsBzUVWvY6Ood1egDyanmTwN2GV"  # обязательно для сессий

# ---- upload settings (без изменений) ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # например 16MB лимит на запрос

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

# Инициализируем БД (создаст таблицы при старте, если ещё нет)
init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/shop")
def shop():
    return render_template("shop.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_panel"))
        else:
            flash("Неправильный логин или пароль", "error")
            return redirect(url_for("admin_login"))

    return render_template("admin-login.html")


@app.route("/admin-panel")
def admin_panel():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    # получаем категории из БД и передаём в шаблон
    db = SessionLocal()
    try:
        categories = db.query(Category).order_by(Category.name).all()
        category_names = [c.name for c in categories]
    finally:
        db.close()

    return render_template("admin-panel.html", categories=category_names)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/admin-panel/add-product", methods=["POST"])
def add_product():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    # Получаем текстовые поля
    name = request.form.get("product-name", "").strip()
    category_name = request.form.get("product-category", "").strip()
    description = request.form.get("product-description", "").strip()

    # Пытаемся получить цену и скидку (если форма их не присылает — 0.0)
    try:
        price = float(request.form.get("product-price", 0) or 0.0)
    except ValueError:
        price = 0.0
    try:
        discount_percent = float(request.form.get("discount_percent", 0) or 0.0)
    except ValueError:
        discount_percent = 0.0

    # Атрибуты — может быть несколько input с name="attribute"
    attributes = request.form.getlist("attribute")
    attributes = [a.strip() for a in attributes if a.strip()]

    # ------------------ Сохранение файлов на диск ------------------
    preview = request.files.get("product-preview")
    preview_saved_path = None
    if preview and preview.filename != "" and allowed_file(preview.filename):
        filename = secure_filename(preview.filename)
        # можно добавить уникальный префикс, чтобы предотвратить коллизии
        save_name = f"preview_{filename}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], save_name)
        preview.save(save_path)
        preview_saved_path = os.path.relpath(
            save_path, BASE_DIR
        )  # например "static/uploads/preview_x.jpg"
    elif preview and preview.filename != "":
        print("Preview file has disallowed extension:", preview.filename)

    images = request.files.getlist("product-images")
    saved_image_paths = []
    for f in images:
        if f and f.filename != "" and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            save_name = f"img_{filename}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], save_name)
            f.save(save_path)
            saved_image_paths.append(os.path.relpath(save_path, BASE_DIR))
        elif f and f.filename != "":
            print("Skipped file (disallowed ext):", f.filename)

    # ------------------ Сохранение в БД ------------------
    db = SessionLocal()
    try:
        # Найдём или создадим категорию
        category = None
        if category_name:
            category = db.query(Category).filter(Category.name == category_name).first()
            if not category:
                category = Category(name=category_name)
                db.add(category)
                db.commit()
                db.refresh(category)

        # Создаём продукт
        product = Product(
            name=name or "Unnamed Product",
            description=description or "",
            price=price,
            discount_percent=discount_percent,
            preview=preview_saved_path,
            category=category,  # SQLAlchemy автоматически выставит category_id
        )
        db.add(product)
        db.commit()
        db.refresh(product)  # теперь у product есть id

        # Добавляем ProductImage записи
        for idx, pth in enumerate(saved_image_paths):
            img = ProductImage(product_id=product.id, path=pth, sort_order=idx)
            db.add(img)
        db.commit()
        db.refresh(product)

        # (опционально) можно хранить attributes где-то — пока просто логируем
        print("=== New product saved to DB ===")
        print("ID:", product.id)
        print("Name:", product.name)
        print("Category:", category.name if category else None)
        print("Price:", product.price)
        print("Discount %:", product.discount_percent)
        print("Preview saved at:", preview_saved_path)
        print("Additional images saved at:", saved_image_paths)
        print("Attributes (raw):", attributes)
        print("===============================")

        flash("Product saved to DB and images stored on disk.", "success")
        return redirect(url_for("admin_panel"))
    except Exception as e:
        db.rollback()
        print("DB error while saving product:", e)
        flash("Ошибка при сохранении продукта. Смотрите логи.", "error")
        return redirect(url_for("admin_panel"))
    finally:
        db.close()


@app.route("/admin-panel/add-category", methods=["POST"])
def add_category():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "not authorized"}), 403

    data = request.get_json(silent=True)
    name = ""
    if data and "name" in data:
        name = str(data["name"]).strip()
    else:
        name = str(request.form.get("name", "")).strip()

    print("Adding category:", name)
    if not name:
        return jsonify({"error": "empty name"}), 400

    db = SessionLocal()
    try:
        # проверим на существование
        exists = db.query(Category).filter(Category.name == name).first()
        if exists:
            return jsonify({"status": "exists", "name": exists.name}), 200

        new_cat = Category(name=name)
        db.add(new_cat)
        db.commit()
        db.refresh(new_cat)
        return jsonify({"status": "ok", "id": new_cat.id, "name": new_cat.name}), 201
    except Exception as e:
        db.rollback()
        print("DB error while adding category:", e)
        return jsonify({"error": "db error"}), 500
    finally:
        db.close()


if __name__ == "__main__":
    app.run(debug=True)
