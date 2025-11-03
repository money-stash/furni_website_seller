from flask import Blueprint, request, jsonify, session
from sqlalchemy.orm import joinedload
from models.models import Cart, CartItem, Product, User
from initdb import SessionLocal
from middlewares.login import login_required, api_login_required

cart_bp = Blueprint("cart", __name__, url_prefix="/api/cart")


@cart_bp.route("/add", methods=["POST"])
@api_login_required
def add_to_cart():
    """Добавить товар в корзину"""
    db = SessionLocal()
    try:
        data = request.get_json()
        product_id = data.get("product_id")
        quantity = data.get("quantity", 1)

        if not product_id:
            return jsonify({"success": False, "message": "ID товару не вказано"}), 400

        # проверяем существование товара
        product = db.query(Product).get(product_id)
        if not product:
            return jsonify({"success": False, "message": "Товар не знайдено"}), 404

        user_id = session["user_id"]

        # получаем или создаём корзину пользователя
        cart = db.query(Cart).filter(Cart.user_id == user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            db.add(cart)
            db.flush()  # чтобы получить cart.id

        # проверяем, есть ли уже этот товар в корзине
        cart_item = (
            db.query(CartItem)
            .filter(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
            .first()
        )

        if cart_item:
            # если товар уже есть — увеличиваем количество
            cart_item.quantity += quantity
        else:
            # создаём новую позицию
            cart_item = CartItem(
                cart_id=cart.id, product_id=product_id, quantity=quantity
            )
            db.add(cart_item)

        db.commit()

        # возвращаем обновлённую информацию о корзине
        cart_data = get_cart_data(db, user_id)

        return jsonify(
            {"success": True, "message": "Товар додано до кошику", "cart": cart_data}
        )

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        db.close()


@cart_bp.route("/remove", methods=["POST"])
@api_login_required
def remove_from_cart():
    """Удалить товар из корзины"""
    db = SessionLocal()
    try:
        data = request.get_json()
        cart_item_id = data.get("cart_item_id")

        if not cart_item_id:
            return jsonify({"success": False, "message": "ID позиції не вказано"}), 400

        user_id = session["user_id"]
        cart = db.query(Cart).filter(Cart.user_id == user_id).first()

        if not cart:
            return jsonify({"success": False, "message": "Кошик не знайдено"}), 404

        cart_item = (
            db.query(CartItem)
            .filter(CartItem.id == cart_item_id, CartItem.cart_id == cart.id)
            .first()
        )

        if not cart_item:
            return jsonify({"success": False, "message": "Позиція не знайдена"}), 404

        db.delete(cart_item)
        db.commit()

        cart_data = get_cart_data(db, user_id)

        return jsonify(
            {"success": True, "message": "Товар видалено з кошику", "cart": cart_data}
        )

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        db.close()


@cart_bp.route("/update", methods=["POST"])
@api_login_required
def update_cart_item():
    """Обновить количество товара в корзине"""
    db = SessionLocal()
    try:
        data = request.get_json()
        cart_item_id = data.get("cart_item_id")
        quantity = data.get("quantity")

        if not cart_item_id or quantity is None:
            return jsonify({"success": False, "message": "Невірні дані"}), 400

        if quantity <= 0:
            return (
                jsonify(
                    {"success": False, "message": "Кількість повинна бути більше 0"}
                ),
                400,
            )

        user_id = session["user_id"]
        cart = db.query(Cart).filter(Cart.user_id == user_id).first()

        if not cart:
            return jsonify({"success": False, "message": "Кошик не знайдено"}), 404

        cart_item = (
            db.query(CartItem)
            .filter(CartItem.id == cart_item_id, CartItem.cart_id == cart.id)
            .first()
        )

        if not cart_item:
            return jsonify({"success": False, "message": "Позиція не знайдена"}), 404

        cart_item.quantity = quantity
        db.commit()

        cart_data = get_cart_data(db, user_id)

        return jsonify(
            {"success": True, "message": "Кількість оновлено", "cart": cart_data}
        )

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        db.close()


@cart_bp.route("/get", methods=["GET"])
@api_login_required
def get_cart():
    """Получить содержимое корзины"""
    db = SessionLocal()
    try:
        user_id = session["user_id"]
        cart_data = get_cart_data(db, user_id)

        return jsonify({"success": True, "cart": cart_data})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        db.close()


def get_cart_data(db, user_id):
    """Вспомогательная функция для получения данных корзины"""
    cart = (
        db.query(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.product))
        .filter(Cart.user_id == user_id)
        .first()
    )

    if not cart:
        return {"items": [], "total_items": 0, "total_price": 0}

    items = [item.as_dict() for item in cart.items]

    return {
        "items": items,
        "total_items": cart.total_items(),
        "total_price": cart.total_price(),
    }
