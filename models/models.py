# models.py
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)

    products = relationship(
        "Product", back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name!r})>"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    price = Column(Float, default=0.0, nullable=False)  # базовая цена
    discount_percent = Column(Float, default=0.0, nullable=False)
    preview = Column(String(512), nullable=True)  # путь к превью/файлу
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    attributes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    images = relationship(
        "ProductImage", back_populates="product", cascade="all, delete-orphan"
    )

    def price_after_discount(self) -> float:
        """Возвращает цену с учётом процента скидки."""
        try:
            discount = max(0.0, min(100.0, float(self.discount_percent or 0.0)))
            return round(float(self.price) * (1.0 - discount / 100.0), 2)
        except Exception:
            return float(self.price or 0.0)

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "discount_percent": self.discount_percent,
            "price_after_discount": self.price_after_discount(),
            "preview": self.preview,
            "images": [img.path for img in self.images],
            "category": self.category.name if self.category else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name!r}, price={self.price})>"


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    path = Column(String(512), nullable=False)
    sort_order = Column(Integer, default=0)  # опционально — порядок отображения

    product = relationship("Product", back_populates="images")

    def __repr__(self):
        return f"<ProductImage(id={self.id}, product_id={self.product_id}, path={self.path!r})>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(150), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    cart = relationship("Cart", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username!r}, phone={self.phone!r})>"


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    def total_price(self) -> float:
        """Возвращает общую сумму всех товаров в корзине."""
        return round(sum(item.subtotal() for item in self.items), 2)

    def total_items(self) -> int:
        """Возвращает общее количество товаров в корзине."""
        return sum(item.quantity for item in self.items)

    def __repr__(self):
        return f"<Cart(id={self.id}, user_id={self.user_id}, items={len(self.items)})>"


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")

    def subtotal(self) -> float:
        """Возвращает стоимость данной позиции (цена со скидкой * количество)."""
        return round(self.product.price_after_discount() * self.quantity, 2)

    def as_dict(self):
        return {
            "id": self.id,
            "product": self.product.as_dict(),
            "quantity": self.quantity,
            "subtotal": self.subtotal(),
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }

    def __repr__(self):
        return f"<CartItem(id={self.id}, product_id={self.product_id}, quantity={self.quantity})>"