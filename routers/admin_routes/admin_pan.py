from flask import Blueprint, app, flash, render_template, request, redirect, url_for
from flask import (
    render_template,
    redirect,
    url_for,
    session,
)

from database.db import get_all_categories
from initdb import SessionLocal
from models.models import Category, Product
from sqlalchemy.orm import joinedload

admin_bp = Blueprint("admin", __name__, template_folder="../templates")


@admin_bp.route("/admin_dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html")


@admin_bp.route("/admin_products")
def admin_products():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    categories = get_all_categories()
    db = SessionLocal()
    try:
        products = (
            db.query(Product)
            .options(joinedload(Product.category))
            .order_by(Product.id.desc())
            .all()
        )

        # DEBUG: проверка
        for p in products:
            if p.id is None:
                print(f"WARNING: Product without ID: {p.name}")

        return render_template(
            "admin-products.html",
            products=products,
            categories=categories,
        )
    finally:
        db.close()


@admin_bp.route("/admin_settings")
def admin_settings():
    return render_template("admin_settings.html")


@admin_bp.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "1234":
            session["admin_logged_in"] = True
            return redirect(url_for("admin.admin_panel"))
        else:
            flash("Неправильный логин или пароль", "error")
            return redirect(url_for("admin.admin_login"))

    return render_template("admin-login.html")


@admin_bp.route("/admin-panel")
def admin_panel():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    # получаем категории из БД и передаём в шаблон
    db = SessionLocal()
    try:
        categories = db.query(Category).order_by(Category.name).all()
        category_names = [c.name for c in categories]
    finally:
        db.close()

    return render_template("admin-panel.html", categories=category_names)
