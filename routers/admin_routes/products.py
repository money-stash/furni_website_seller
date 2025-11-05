import os
from werkzeug.utils import secure_filename

from initdb import SessionLocal
from models.models import (
    Category,
    Product,
    ProductImage,
    AddOnCategory,
    AddOnItem,
)
from sqlalchemy.orm import joinedload

from flask import Blueprint, flash, render_template, request, redirect, session, url_for

from config import UPLOAD_FOLDER, ALLOWED_EXT, BASE_DIR

products_bp = Blueprint("products", __name__, template_folder="../templates")


@products_bp.route("/update_product/<int:product_id>", methods=["GET", "POST"])
def update_product(product_id):
    db = SessionLocal()
    try:
        product = (
            db.query(Product)
            .options(
                joinedload(Product.images),
                joinedload(Product.category),
                joinedload(Product.addon_categories).joinedload(AddOnCategory.items),
            )
            .get(product_id)
        )
        categories = db.query(Category).order_by(Category.name).all()
        if request.method == "GET":
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

        name = request.form.get("product-name", "").strip()
        description = request.form.get("product-description", "").strip()
        price = float(request.form.get("product-price", 0) or 0)
        discount_percent = float(request.form.get("discount_percent", 0) or 0)
        category_id = request.form.get("product-category")
        delete_preview = request.form.get("delete_preview") == "1"

        product.name = name
        product.description = description
        product.price = price
        product.discount_percent = discount_percent
        product.category_id = int(category_id) if category_id else None

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

        keep_images = request.form.getlist("existing_images")
        keep_images = [p for p in keep_images if p]
        for img in list(product.images):
            if img.path not in keep_images:
                try:
                    full_path = os.path.join(BASE_DIR, img.path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                except Exception as e:
                    print("Cannot delete product image file:", e)
                try:
                    db.delete(img)
                except Exception as e:
                    print("Cannot delete ProductImage record:", e)

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

        existing_addon_ids = [
            int(i) for i in request.form.getlist("existing_addon_category_ids") if i
        ]
        for addon in list(product.addon_categories):
            if addon.id not in existing_addon_ids:
                for item in list(addon.items):
                    try:
                        full_path = os.path.join(BASE_DIR, item.image_path)
                        if os.path.exists(full_path):
                            os.remove(full_path)
                    except Exception as e:
                        print("Cannot delete addon item file:", e)
                    try:
                        db.delete(item)
                    except Exception as e:
                        print("Cannot delete AddOnItem record:", e)
                try:
                    db.delete(addon)
                except Exception as e:
                    print("Cannot delete AddOnCategory record:", e)

        for addon_id_str in request.form.getlist("existing_addon_category_ids"):
            if not addon_id_str:
                continue
            try:
                addon_id = int(addon_id_str)
            except ValueError:
                continue
            addon = next(
                (a for a in product.addon_categories if a.id == addon_id), None
            )
            if not addon:
                continue
            name_field = request.form.get(f"addon_name_{addon_id}", "").strip()
            price_field = request.form.get(f"addon_price_{addon_id}", "")
            try:
                price_val = float(price_field or 0)
            except Exception:
                price_val = 0.0
            addon.name = name_field or addon.name
            addon.price = price_val

            # Обработка существующих элементов addon с их именами
            keep_items_ids = request.form.getlist(f"existing_addon_item_ids_{addon_id}")
            keep_items_ids = [int(i) for i in keep_items_ids if i]

            for item in list(addon.items):
                if item.id not in keep_items_ids:
                    # Удаляем элемент
                    if item.image_path:
                        try:
                            full_path = os.path.join(BASE_DIR, item.image_path)
                            if os.path.exists(full_path):
                                os.remove(full_path)
                        except Exception as e:
                            print("Cannot delete addon item file:", e)
                    try:
                        db.delete(item)
                    except Exception as e:
                        print("Cannot delete AddOnItem record:", e)
                else:
                    # Обновляем имя элемента
                    item_name = request.form.get(
                        f"addon_item_name_{addon_id}_{item.id}", ""
                    ).strip()
                    if item_name:
                        item.name = item_name

            # Добавление новых элементов к существующей категории
            files_key = f"addon_items_{addon_id}"
            names_key = f"addon_item_names_{addon_id}[]"
            if files_key in request.files:
                files = request.files.getlist(files_key)
                names = request.form.getlist(names_key)
                for idx, f in enumerate(files):
                    if f and f.filename != "":
                        filename = secure_filename(f.filename)
                        save_name = f"addon_{addon_id}_{filename}"
                        save_path = os.path.join(UPLOAD_FOLDER, save_name)
                        f.save(save_path)

                        item_name = names[idx].strip() if idx < len(names) else ""
                        if not item_name:
                            item_name = f"Элемент {idx + 1}"

                        item = AddOnItem(
                            addon_category_id=addon.id,
                            name=item_name,
                            image_path=os.path.relpath(save_path, BASE_DIR),
                        )
                        db.add(item)

        # Обработка новых категорий addon
        new_addon_names = request.form.getlist("addon_name_new[]")
        new_addon_prices = request.form.getlist("addon_price_new[]")
        for idx, name_new in enumerate(new_addon_names):
            name_new = (name_new or "").strip()
            price_new_raw = (
                new_addon_prices[idx] if idx < len(new_addon_prices) else "0"
            )
            try:
                price_new = float(price_new_raw or 0)
            except Exception:
                price_new = 0.0
            if not name_new:
                continue
            new_addon = AddOnCategory(
                product_id=product.id, name=name_new, price=price_new
            )
            db.add(new_addon)
            db.flush()

            files_key_new = f"addon_items_new_{idx}"
            names_key_new = f"addon_item_names_new_{idx}[]"
            if files_key_new in request.files:
                files = request.files.getlist(files_key_new)
                names = request.form.getlist(names_key_new)
                for file_idx, f in enumerate(files):
                    if f and f.filename != "":
                        filename = secure_filename(f.filename)
                        save_name = f"addon_new_{new_addon.id}_{filename}"
                        save_path = os.path.join(UPLOAD_FOLDER, save_name)
                        f.save(save_path)

                        item_name = (
                            names[file_idx].strip() if file_idx < len(names) else ""
                        )
                        if not item_name:
                            item_name = f"Элемент {file_idx + 1}"

                        item = AddOnItem(
                            addon_category_id=new_addon.id,
                            name=item_name,
                            image_path=os.path.relpath(save_path, BASE_DIR),
                        )
                        db.add(item)

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
