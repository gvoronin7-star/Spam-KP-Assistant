"""
Базовые тесты
"""
import pytest
from pathlib import Path
import sys

# Добавление корня проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import_core():
    """Тест импорта модулей ядра"""
    from core.database import engine, SessionLocal
    from core.models import Profile, Contact, Template, Dialogue, Message
    
    assert engine is not None
    assert SessionLocal is not None


def test_import_utils():
    """Тест импорта утилит"""
    # Импортируем напрямую, чтобы избежать проблем с validators
    from utils.encryption import encryption
    
    assert encryption is not None


def test_import_services():
    """Тест импорта сервисов"""
    from services.contact_importer import import_contacts
    from services.smtp_manager import SMTPManager
    from services.llm_service import LLMService
    
    assert import_contacts is not None
    assert SMTPManager is not None
    assert LLMService is not None


def test_encryption():
    """Тест шифрования"""
    from utils.encryption import encryption
    
    test_data = "test_password_123"
    encrypted = encryption.encrypt(test_data)
    decrypted = encryption.decrypt(encrypted)
    
    assert decrypted == test_data


def test_database_init():
    """Тест инициализации БД"""
    from core.database import init_db, engine
    
    # Создаём таблицы
    init_db()
    
    # Проверяем, что таблицы созданы
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    assert "profiles" in tables
    assert "contacts" in tables
    assert "templates" in tables
    assert "dialogues" in tables
    assert "messages" in tables
    assert "tasks" in tables
