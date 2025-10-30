import os
from werkzeug.utils import secure_filename

from initdb import SessionLocal
from models.models import (
    Category,
    Product,
    ProductImage,
)
from sqlalchemy.orm import joinedload

from flask import Blueprint, flash, render_template, request, redirect, session, url_for
from flask import (
    render_template,
    redirect,
    url_for,
)

from config import UPLOAD_FOLDER, ALLOWED_EXT, BASE_DIR

from initdb import SessionLocal
from models.models import Category, Product
from sqlalchemy.orm import joinedload

products_bp = Blueprint("products", __name__, template_folder="../templates")


@products_bp.route("/update_product/<int:product_id>", methods=["GET", "POST"])
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


def _is_within_directory(path, directory):
    path = os.path.realpath(path)
    directory = os.path.realpath(directory)
    return os.path.commonpath([path]) == os.path.commonpath([path, directory])


@products_bp.route("/delete_product/<int:product_id>", methods=["GET", "POST"])
def delete_product(product_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    db = SessionLocal()
    try:
        product = db.query(Product).options(joinedload(Product.images)).get(product_id)
        if request.method == "GET":
            if not product:
                flash("Товар не найден", "error")
                return redirect(url_for("admin.admin_products"))
            return render_template("delete_product.html", product=product)
        # POST -> удалить
        if not product:
            flash("Товар не найден", "error")
            return redirect(url_for("admin.admin_products"))
        if product.preview:
            try:
                full_preview = os.path.join(BASE_DIR, product.preview)
                if os.path.exists(full_preview) and _is_within_directory(
                    full_preview, BASE_DIR
                ):
                    os.remove(full_preview)
            except Exception as e:
                print("Error deleting preview file:", e)
        for img in list(product.images):
            try:
                full_img = os.path.join(BASE_DIR, img.path)
                if os.path.exists(full_img) and _is_within_directory(
                    full_img, BASE_DIR
                ):
                    os.remove(full_img)
            except Exception as e:
                print("Error deleting product image file:", e)
            try:
                db.delete(img)
            except Exception as e:
                print("Error deleting ProductImage record:", e)
        try:
            db.delete(product)
            db.commit()
            flash("Товар удалён", "success")
        except Exception as e:
            db.rollback()
            print("DB error while deleting product:", e)
            flash("Ошибка при удалении товара. Смотрите логи.", "error")
        return redirect(url_for("admin.admin_products"))
    finally:
        db.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@products_bp.route("/admin-panel/add-product", methods=["POST"])
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
        save_path = os.path.join(UPLOAD_FOLDER, save_name)
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
            save_path = os.path.join(UPLOAD_FOLDER, save_name)
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
        return redirect(url_for("admin.admin_panel"))
    except Exception as e:
        db.rollback()
        print("DB error while saving product:", e)
        flash("Ошибка при сохранении продукта. Смотрите логи.", "error")
        return redirect(url_for("admin.admin_panel"))
    finally:
        db.close()
