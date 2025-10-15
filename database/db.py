from initdb import SessionLocal
from models.models import Category


def get_all_categories():
    """Возвращает список всех категорий из базы данных."""
    db = SessionLocal()
    try:
        categories = db.query(Category).order_by(Category.name).all()
        return categories
    finally:
        db.close()
