from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Base

DB_PATH = "sqlite:///./app.db"  # файл app.db в текущей папке
engine = create_engine(DB_PATH, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    print("DB created / checked.")


if __name__ == "__main__":
    init_db()
