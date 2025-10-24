import os
from flask import (
    Blueprint,
    jsonify,
    request,
)
from flask import session


from config import BASE_DIR
from initdb import SessionLocal
from models.models import Category, Product, ProductImage

categories_bp = Blueprint("categories", __name__, template_folder="../templates")


@categories_bp.route("/admin-panel/delete-category", methods=["POST"])
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


@categories_bp.route("/admin-panel/add-category", methods=["POST"])
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
