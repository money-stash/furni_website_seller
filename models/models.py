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
