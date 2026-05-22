"""
База данных SQLite + SQLAlchemy
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from loguru import logger

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'spam_kp_assistant.db'}"

engine = create_engine(
    DATABASE_URL,
    echo=False,  # Включить для отладки SQL-запросов
    connect_args={"check_same_thread": False}  # Для SQLite + многопоточности
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Получить сессию БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Инициализировать базу данных (создать таблицы)"""
    logger.info(f"Инициализация БД: {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы созданы успешно")


if __name__ == "__main__":
    init_db()
    logger.info("База данных инициализирована")
