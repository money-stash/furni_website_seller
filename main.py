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
from routers.user_routes import user_reg, auth
from routers.admin_routes import admin_pan, products
from sqlalchemy.orm import joinedload

from middlewares.login import login_required

from config import UPLOAD_FOLDER, ALLOWED_EXT, BASE_DIR

app = Flask(__name__)
app.secret_key = "Lql8aLsBzUVWvY6Ood1egDyanmTwN2GV"  # обязательно для сессий

app.register_blueprint(user_reg.reg_bp)
app.register_blueprint(auth.auth)
app.register_blueprint(admin_pan.admin_bp)
app.register_blueprint(products.products_bp)

# ---- upload settings (без изменений) ----

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@app.route("/cart")
def cart():
    return render_template("cart.html")


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
