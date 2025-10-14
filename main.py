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


@app.route("/admin-panel/delete-category", methods=["POST"])
def delete_category():
    """Удаляет категорию по имени"""
    if not session.get("admin_logged_in"):
        print("ERROR: Not authorized")
        return jsonify({"error": "not authorized"}), 403

    data = request.get_json(silent=True)
    print(f"DEBUG: Received JSON data: {data}")
    print(f"DEBUG: Request form data: {dict(request.form)}")

    name = ""
    if data and "name" in data:
        name = str(data["name"]).strip()
    else:
        name = str(request.form.get("name", "")).strip()

    # Опциональный параметр: каскадное удаление
    cascade = data.get("cascade", False) if data else False

    print(
        f"DEBUG: Category name to delete: '{name}' (length: {len(name)}), cascade: {cascade}"
    )
    if not name:
        print("ERROR: Empty name")
        return jsonify({"error": "empty name"}), 400

    db = SessionLocal()
    try:
        # Находим категорию
        category = db.query(Category).filter(Category.name == name).first()
        print(f"DEBUG: Found category: {category}")
        if not category:
            print(f"ERROR: Category '{name}' not found in DB")
            all_cats = db.query(Category).all()
            print(f"DEBUG: Available categories: {[c.name for c in all_cats]}")
            return jsonify({"error": "category not found"}), 404

        # Проверяем, есть ли товары в этой категории
        products = db.query(Product).filter(Product.category_id == category.id).all()
        products_count = len(products)
        print(f"DEBUG: Products in category: {products_count}")

        if products_count > 0:
            if not cascade:
                # Без каскадного удаления — возвращаем ошибку с количеством товаров
                print(
                    f"ERROR: Cannot delete category with {products_count} products (cascade not enabled)"
                )
                return (
                    jsonify(
                        {
                            "error": f"Category has {products_count} product(s)",
                            "products_count": products_count,
                            "suggestion": "Delete products first or enable cascade delete",
                        }
                    ),
                    400,
                )
            else:
                # С каскадным удалением — удаляем все товары и их изображения
                print(
                    f"INFO: Cascade delete enabled, removing {products_count} products"
                )
                for product in products:
                    # Удаляем связанные изображения
                    images = (
                        db.query(ProductImage)
                        .filter(ProductImage.product_id == product.id)
                        .all()
                    )
                    for img in images:
                        # Опционально: удаляем файлы с диска
                        if img.path:
                            full_path = os.path.join(BASE_DIR, img.path)
                            if os.path.exists(full_path):
                                try:
                                    os.remove(full_path)
                                    print(f"  Deleted file: {full_path}")
                                except Exception as e:
                                    print(f"  Failed to delete file {full_path}: {e}")
                        db.delete(img)

                    # Удаляем preview файл товара
                    if product.preview:
                        full_path = os.path.join(BASE_DIR, product.preview)
                        if os.path.exists(full_path):
                            try:
                                os.remove(full_path)
                                print(f"  Deleted preview: {full_path}")
                            except Exception as e:
                                print(f"  Failed to delete preview {full_path}: {e}")

                    # Удаляем сам товар
                    db.delete(product)
                    print(f"  Deleted product: {product.name} (id={product.id})")

        # Удаляем категорию
        db.delete(category)
        db.commit()

        print(f"SUCCESS: Category '{name}' (id={category.id}) deleted successfully")
        return (
            jsonify({"status": "ok", "name": name, "deleted_products": products_count}),
            200,
        )
    except Exception as e:
        db.rollback()
        print(f"ERROR: DB error while deleting category: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": "db error", "detail": str(e)}), 500
    finally:
        db.close()


# Добавьте этот роут для передачи URL в JS
@app.context_processor
def inject_urls():
    """Добавляет URLs в контекст всех шаблонов"""
    return {
        "urls": {
            "delete_category": url_for("delete_category"),
            "add_category": url_for("add_category"),
        }
    }


if __name__ == "__main__":
    app.run(debug=True)
