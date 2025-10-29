import json
import os
from types import SimpleNamespace
from flask import (
    Flask,
    render_template,
    redirect,
    request,
    url_for,
    session,
    flash,
)
from sqlalchemy.orm import joinedload

from models.models import Cart, CartItem, Product, User, Category
from initdb import SessionLocal, init_db
from database.db import get_all_categories

from routers.user_routes import user_reg, auth, cart_routes
from routers.admin_routes import admin_pan, products, categories

from middlewares.login import login_required

from config import UPLOAD_FOLDER


app = Flask(__name__)
app.secret_key = "Lql8aLsBzUVWvY6Ood1egDyanmTwN2GV"  # обязательно для сессий

app.register_blueprint(user_reg.reg_bp)
app.register_blueprint(auth.auth)
app.register_blueprint(admin_pan.admin_bp)
app.register_blueprint(products.products_bp)
app.register_blueprint(categories.categories_bp)
app.register_blueprint(cart_routes.cart_bp)

# ---- upload settings (без изменений) ----

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB лимит на запрос

init_db()


@app.route("/")
def index():
    db = SessionLocal()
    try:
        data_path = os.path.join(os.getcwd(), "data.json")
        selected_ids = []
        selected_categories = []

        if os.path.exists(data_path):
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
            except:
                d = {}

            selected_ids = [int(x) for x in d.get("selected_categories", []) if x]

            if not selected_ids:
                product_ids = [int(x) for x in d.get("selected_products", []) if x]
                if product_ids:
                    products = [db.get(Product, pid) for pid in product_ids]
                    seen = set()
                    ordered_cat_ids = []
                    for p in products:
                        if p and p.category:
                            cid = p.category.id
                            if cid not in seen:
                                seen.add(cid)
                                ordered_cat_ids.append(cid)
                    selected_ids = ordered_cat_ids

        if selected_ids:
            cats = db.query(Category).filter(Category.id.in_(selected_ids)).all()
            cats_by_id = {c.id: c for c in cats}
            selected_categories = [
                cats_by_id[i] for i in selected_ids if i in cats_by_id
            ]

        return render_template("index.html", selected_categories=selected_categories)
    finally:
        db.close()


@app.route("/categories")
def categories_view():
    db = SessionLocal()
    try:
        cats = db.query(Category).all()
        cats.sort(
            key=lambda c: (
                (c.tier if c.tier is not None else 0),
                (c.name or "").lower(),
            )
        )
        out = []
        for c in cats:
            img = None
            if c.image_path:
                p = c.image_path.strip()
                if p.startswith("http://") or p.startswith("https://"):
                    img = p
                else:
                    img = url_for("static", filename=p)
            else:
                img = None
            out.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "image_url": img,
                    "tier": c.tier if c.tier is not None else 0,
                }
            )
        return render_template("categories.html", categories=out)
    finally:
        db.close()


@app.route("/shop")
def shop():
    db = SessionLocal()
    try:
        selected_category = request.args.get("category", "all")

        # загружаем продукты с предзагрузкой связей чтобы избежать N+1
        products = (
            db.query(Product)
            .options(joinedload(Product.images), joinedload(Product.category))
            .order_by(Product.id.desc())
            .all()
        )

        categories = get_all_categories()

        return render_template(
            "shop.html",
            products=products,
            categories=categories,
            selected_category=selected_category,
        )
    finally:
        db.close()


@app.route("/product/<int:product_id>")
def product_info(product_id):
    db = SessionLocal()
    try:
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
    db = SessionLocal()
    try:
        data_path = os.path.join(os.getcwd(), "data.json")
        selected_ids = []
        selected_categories = []

        if os.path.exists(data_path):
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
            except:
                d = {}

            selected_ids = [int(x) for x in d.get("selected_categories", []) if x]

            if not selected_ids:
                product_ids = [int(x) for x in d.get("selected_products", []) if x]
                if product_ids:
                    products = [db.get(Product, pid) for pid in product_ids]
                    seen = set()
                    ordered_cat_ids = []
                    for p in products:
                        if p and p.category:
                            cid = p.category.id
                            if cid not in seen:
                                seen.add(cid)
                                ordered_cat_ids.append(cid)
                    selected_ids = ordered_cat_ids

        if selected_ids:
            cats = db.query(Category).filter(Category.id.in_(selected_ids)).all()
            cats_by_id = {c.id: c for c in cats}
            selected_categories = [
                cats_by_id[i] for i in selected_ids if i in cats_by_id
            ]

        return render_template("services.html", selected_categories=selected_categories)
    finally:
        db.close()


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/terms")
def terms():
    return render_template("user_agreement.html")


@app.route("/profile")
@login_required
def profile():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == session["user_id"]).first()
        if not user:
            session.clear()
            return redirect(url_for("auth.login"))

        return render_template("profile.html", user=user)
    finally:
        db.close()


@app.route("/cart")
@login_required
def cart():
    db = SessionLocal()
    try:
        user_id = session["user_id"]

        # получаем корзину пользователя с товарами
        cart_obj = (
            db.query(Cart)
            .options(
                joinedload(Cart.items)
                .joinedload(CartItem.product)
                .joinedload(Product.images)
            )
            .filter(Cart.user_id == user_id)
            .first()
        )

        # если корзины нет - создаём пустую структуру
        if not cart_obj:
            # Используем SimpleNamespace, чтобы в шаблонах dot-notation работала как ожидается
            cart_data = SimpleNamespace(items=[], total_price=0.0, total_items=0)
        else:
            # Преобразуем relationship в список
            items_list = list(cart_obj.items)
            # Убедимся, что total_price возвращается числом (float)
            try:
                total_price = float(cart_obj.total_price())
            except Exception:
                total_price = 0.0
            try:
                total_items = int(cart_obj.total_items())
            except Exception:
                total_items = len(items_list)

            cart_data = SimpleNamespace(
                items=items_list,
                total_price=total_price,
                total_items=total_items,
            )

        return render_template("cart.html", cart=cart_data)
    finally:
        db.close()


@app.route("/forgot-password")
def forgot_password():
    return render_template("forgot_password.html")


# добавить этот роут для передачи url в js
@app.context_processor
def inject_urls():
    """Добавляет URLs в контекст всех шаблонов"""
    return {
        "urls": {
            "delete_category": url_for("categories.delete_category"),
            "add_category": url_for("categories.add_category"),
        }
    }


if __name__ == "__main__":
    app.run(debug=True)
