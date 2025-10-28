import json
import os
from flask import Blueprint, app, flash, render_template, request, redirect, url_for
from flask import (
    render_template,
    redirect,
    url_for,
    session,
)

from initdb import SessionLocal
from sqlalchemy.orm import joinedload
from models.models import Category, Product
from database.db import get_all_categories

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

    db = SessionLocal()
    try:
        categories = db.query(Category).order_by(Category.name).all()
        # Передаём и имя, и путь к изображению
        category_data = [
            {"name": c.name, "image_path": c.image_path} for c in categories
        ]
    finally:
        db.close()

    return render_template("admin-panel.html", categories=category_data)


@admin_bp.route("/admin_settings", methods=["GET", "POST"])
def admin_settings():
    db = SessionLocal()
    try:
        products = db.query(Product).order_by(Product.id.desc()).all()

        saved_selected = None
        data_path = os.path.join(os.getcwd(), "data.json")
        if os.path.exists(data_path):
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    saved_selected = d.get("selected_products")
            except:
                saved_selected = None

        if request.method == "POST":
            p1 = request.form.get("product_1") or None
            p2 = request.form.get("product_2") or None
            p3 = request.form.get("product_3") or None
            selected = [p1, p2, p3]
            data = {"selected_products": [int(x) if x else None for x in selected]}
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return redirect(url_for("admin.admin_settings", saved=1))

        saved = request.args.get("saved") is not None
        print(products)
        return render_template(
            "admin_settings.html",
            products=products,
            saved=saved,
            selected=saved_selected,
        )
    finally:
        db.close()
