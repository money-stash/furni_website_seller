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

from database.db import get_all_categories
from initdb import SessionLocal, init_db
from models.models import (
    Category,
    Product,
    ProductImage,
)
from routers.user_routes import user_reg
from routers.admin_routes import admin_pan
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.secret_key = "Lql8aLsBzUVWvY6Ood1egDyanmTwN2GV"  # обязательно для сессий

app.register_blueprint(user_reg.reg_bp)
app.register_blueprint(admin_pan.admin_bp)

# ---- upload settings (без изменений) ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB лимит на запрос

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/shop")
def shop():
    """
    Передаём в шаблон все продукты (связанные category и images),
    чтобы можно было вывести их на странице shop.
    """
    db = SessionLocal()
    try:
        # загружаем продукты с предзагрузкой связей чтобы избежать N+1
        products = (
            db.query(Product)
            .options(joinedload(Product.images), joinedload(Product.category))
            .order_by(Product.id.desc())
            .all()
        )

        # категории (если нужно показывать фильтры/список категорий на странице)
        categories = get_all_categories()

        return render_template(
            "shop.html",
            products=products,
            categories=categories,
        )
    finally:
        db.close()


@app.route("/update_product/<int:product_id>", methods=["GET", "POST"])
def update_product(product_id):
    db = SessionLocal()
    try:
        product = (
            db.query(Product)
            .options(joinedload(Product.images), joinedload(Product.category))
            .get(product_id)
        )
        categories = db.query(Category).order_by(Category.name).all()
        if request.method == "GET":
            # Передаем список атрибутов (если есть)
            attributes = []
            if product and getattr(product, "attributes", None):
                try:
                    attributes = [a for a in product.attributes.split(";") if a]
                except Exception:
                    attributes = []

            return render_template(
                "edit_product.html",
                product=product,
                categories=categories,
                attributes=attributes,
            )

        # POST: обработка формы
        name = request.form.get("product-name", "").strip()
        description = request.form.get("product-description", "").strip()
        price = float(request.form.get("product-price", 0) or 0)
        discount_percent = float(request.form.get("discount_percent", 0) or 0)
        category_id = request.form.get("product-category")
        delete_preview = request.form.get("delete_preview") == "1"

        # обновляем поля
        product.name = name
        product.description = description
        product.price = price
        product.discount_percent = discount_percent
        product.category_id = int(category_id) if category_id else None

        # Обработка превью
        preview_file = request.files.get("product-preview")
        if delete_preview and product.preview:
            try:
                full_path = os.path.join(BASE_DIR, product.preview)
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as e:
                print("Cannot delete preview:", e)
            product.preview = None
        if preview_file and preview_file.filename != "":
            filename = secure_filename(preview_file.filename)
            save_name = f"preview_{filename}"
            save_path = os.path.join(UPLOAD_FOLDER, save_name)
            preview_file.save(save_path)
            product.preview = os.path.relpath(save_path, BASE_DIR)

        # На фронте для оставшихся изображений приходят hidden inputs name="existing_images".
        # Соберём список тех путей, которые остались, и удалим все ProductImage, которые есть в БД, но которых нет в этом списке.
        keep_images = request.form.getlist(
            "existing_images"
        )  # список путей (точно такие же строки, что в img.path)
        # Нормализация: уберём пустые значения
        keep_images = [p for p in keep_images if p]
        # Создаём копию списка product.images, т.к. будем удалять элементы
        for img in list(product.images):
            # img.path должен совпадать со значением в hidden input; при необходимости нормализуй формат сравнения
            if img.path not in keep_images:
                # удаляем файл с диска (если существует)
                try:
                    full_path = os.path.join(BASE_DIR, img.path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except Exception as e:
                    print("Cannot delete product image file:", e)
                # удаляем запись из сессии/БД
                try:
                    db.delete(img)
                except Exception as e:
                    print("Cannot delete ProductImage record:", e)

        # Обработка дополнительных изображений (новые файлы)
        new_images = request.files.getlist("product-images")
        for f in new_images:
            if f and f.filename != "":
                filename = secure_filename(f.filename)
                save_name = f"img_{filename}"
                save_path = os.path.join(UPLOAD_FOLDER, save_name)
                f.save(save_path)
                img = ProductImage(
                    product_id=product.id, path=os.path.relpath(save_path, BASE_DIR)
                )
                db.add(img)

        # Сохраняем атрибуты — поддерживаем два формата:
        # 1) одна строка 'attributes' (например "size;color;material") — форму собирает JS
        # 2) несколько полей 'attribute' (обычная HTML-форма)
        attributes_field = request.form.get("attributes")
        if attributes_field:
            form_attributes = [
                a.strip() for a in attributes_field.split(";") if a.strip()
            ]
        else:
            form_attributes = [
                a.strip() for a in request.form.getlist("attribute") if a.strip()
            ]

        product.attributes = ";".join(form_attributes) if form_attributes else None

        db.commit()
        flash("Товар обновлен", "success")
        return redirect(url_for("admin.admin_products"))

    except Exception as e:
        db.rollback()
        print("Update product error:", e)
        flash("Ошибка при обновлении товара", "error")
        return redirect(url_for("admin.admin_products"))
    finally:
        db.close()


@app.route("/delete_product/<int:product_id>")
def delete_product(product_id):
    return render_template("delete_product.html", product_id=product_id)


@app.route("/product/<int:product_id>")
def product_info(product_id):
    db = SessionLocal()
    try:
        # загружаем товар с изображениями и категорией
        product = (
            db.query(Product)
            .options(joinedload(Product.images), joinedload(Product.category))
            .get(product_id)
        )
        if not product:
            flash("Товар не знайдено", "error")
            return redirect(url_for("shop"))

        return render_template("product_info.html", product=product)
    finally:
        db.close()


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


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
    attributes_str = ";".join(attributes) if attributes else None
    print("Received attributes:", attributes)

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
            attributes=attributes_str,
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


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/forgot-password")
def forgot_password():
    return render_template("forgot_password.html")


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
