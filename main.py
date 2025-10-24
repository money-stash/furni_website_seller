import os
from types import SimpleNamespace
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    flash,
)
from sqlalchemy.orm import joinedload

from models.models import Cart, CartItem, Product, User
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
