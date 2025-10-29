import os
from uuid import uuid4
from flask import (
    Blueprint,
    jsonify,
    request,
    url_for,
)
from flask import session
from werkzeug.utils import secure_filename

from config import BASE_DIR
from initdb import SessionLocal
from models.models import Category, Product, ProductImage

categories_bp = Blueprint("categories", __name__, template_folder="../templates")


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

        # Найти максимальный tier и добавить новую категорию в конец
        max_tier = db.query(Category).count()

        new_cat = Category(name=name, tier=max_tier)
        db.add(new_cat)
        db.commit()
        db.refresh(new_cat)
        return (
            jsonify(
                {
                    "status": "ok",
                    "id": new_cat.id,
                    "name": new_cat.name,
                    "tier": new_cat.tier,
                    "image_path": new_cat.image_path,
                }
            ),
            201,
        )
    except Exception as e:
        db.rollback()
        print("DB error while adding category:", e)
        return jsonify({"error": "db error"}), 500
    finally:
        db.close()


ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def allowed_filename(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXT


def admin_required_json():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    return None


@categories_bp.route("/upload-image", methods=["POST"])
def upload_category_image():
    auth_err = admin_required_json()
    if auth_err:
        return auth_err

    if "category_name" not in request.form or "image" not in request.files:
        return jsonify({"error": "Missing data"}), 400

    category_name = request.form["category_name"]
    img = request.files["image"]

    if img.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_filename(img.filename):
        return jsonify({"error": "Invalid file extension"}), 400

    img.seek(0, os.SEEK_END)
    size = img.tell()
    img.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({"error": "File too large"}), 400

    filename = secure_filename(img.filename)
    unique_name = f"{uuid4().hex}_{filename}"
    upload_rel_dir = "uploads/categories"
    upload_dir = os.path.join("static/", upload_rel_dir)
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, unique_name)
    img.save(save_path)

    image_path = f"{upload_rel_dir}/{unique_name}"

    db = SessionLocal()
    try:
        cat = db.query(Category).filter(Category.name == category_name).first()
        if not cat:
            try:
                os.remove(save_path)
            except Exception:
                pass
            return jsonify({"error": "Category not found"}), 404

        # удалить старый файл, если он был
        old = cat.image_path
        if old:
            try:
                old_full = os.path.join("static/", old)
                if os.path.exists(old_full):
                    os.remove(old_full)
            except Exception:
                pass

        cat.image_path = image_path
        db.add(cat)
        db.commit()
        db.refresh(cat)

        image_url = url_for("static", filename=image_path)
        return jsonify({"image_path": image_path, "image_url": image_url})
    finally:
        db.close()


@categories_bp.route("/delete", methods=["POST"])
def delete_category():
    """
    Ожидает JSON: { "name": "<category name>" }
    Удаляет категорию (и файл изображения, если есть).
    """
    auth_err = admin_required_json()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data or "name" not in data:
        return jsonify({"error": "Missing 'name' in request"}), 400

    name = data["name"]
    db = SessionLocal()
    try:
        cat = db.query(Category).filter(Category.name == name).first()
        if not cat:
            return jsonify({"error": "Category not found"}), 404

        deleted_tier = cat.tier

        # Удаляем файл изображения если есть
        if cat.image_path:
            try:
                full = os.path.join("static/", cat.image_path)
                if os.path.exists(full):
                    os.remove(full)
            except Exception:
                pass

        db.delete(cat)

        # Обновить tier всех категорий после удалённой
        db.query(Category).filter(Category.tier > deleted_tier).update(
            {Category.tier: Category.tier - 1}, synchronize_session=False
        )

        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@categories_bp.route("/reorder", methods=["POST"])
def reorder_categories():
    """
    Ожидает JSON: { "order": ["category_name1", "category_name2", ...] }
    Обновляет tier всех категорий согласно новому порядку.
    """
    auth_err = admin_required_json()
    if auth_err:
        return auth_err

    data = request.get_json(silent=True)
    if not data or "order" not in data:
        return jsonify({"error": "Missing 'order' in request"}), 400

    order = data["order"]
    if not isinstance(order, list):
        return jsonify({"error": "'order' must be an array"}), 400

    db = SessionLocal()
    try:
        # Обновить tier для каждой категории
        for idx, category_name in enumerate(order):
            cat = db.query(Category).filter(Category.name == category_name).first()
            if cat:
                cat.tier = idx
                db.add(cat)

        db.commit()
        return jsonify({"success": True, "updated": len(order)})
    except Exception as e:
        db.rollback()
        print(f"Error reordering categories: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
