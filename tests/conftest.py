"""
Pytest конфигурация и общие fixtures
"""
import pytest
import sys
from pathlib import Path

# Добавление корня проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_data_dir():
    """Путь к тестовым данным"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="function")
def test_db():
    """Тестовая БД (в памяти)"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.database import Base
    
    # Создаём БД в памяти
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    
    db = Session()
    yield db
    db.close()


@pytest.fixture(scope="function")
def test_profile(test_db):
    """Тестовый профиль"""
    from core.models import Profile
    
    profile = Profile(
        name="Тестовый профиль",
        description="Профиль для тестирования",
        tech_params={"speed": "100 Мбит/с", "protocol": "Ethernet"},
        requirements={"price": True, "term": True},
        dialogue_rules={"qa_pairs": []},
        attachments=[],
        is_active=True
    )
    
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    
    yield profile
    
    test_db.delete(profile)
    test_db.commit()


@pytest.fixture(scope="function")
def test_contact(test_db):
    """Тестовый контакт"""
    from core.models import Contact
    
    contact = Contact(
        email="test@example.com",
        company_name="Тестовая компания",
        contact_person="Иван Тестов",
        notes="Тестовый контакт",
        is_active=True
    )
    
    test_db.add(contact)
    test_db.commit()
    test_db.refresh(contact)
    
    yield contact
    
    test_db.delete(contact)
    test_db.commit()


@pytest.fixture(scope="function")
def test_template(test_db):
    """Тестовый шаблон"""
    from core.models import Template
    
    template = Template(
        name="Тестовый шаблон",
        template_type="initial",
        subject="Тестовая тема",
        body_plain="Тестовый текст",
        body_html="<html><body>Тест</body></html>",
        attachments=[],
        version=1,
        is_active=True
    )
    
    test_db.add(template)
    test_db.commit()
    test_db.refresh(template)
    
    yield template
    
    test_db.delete(template)
    test_db.commit()


@pytest.fixture(scope="function")
def test_dialogue(test_db, test_profile, test_contact):
    """Тестовый диалог"""
    from core.models import Dialogue
    
    dialogue = Dialogue(
        profile_id=test_profile.id,
        contact_id=test_contact.id,
        status="sent",
        kp_received=False
    )
    
    test_db.add(dialogue)
    test_db.commit()
    test_db.refresh(dialogue)
    
    yield dialogue
    
    test_db.delete(dialogue)
    test_db.commit()


@pytest.fixture(scope="function")
def encryption():
    """Тестовый менеджер шифрования"""
    from utils.encryption import encryption
    yield encryption


@pytest.fixture(scope="function")
def sample_csv_file(test_data_dir, tmp_path):
    """Создание тестового CSV файла"""
    import csv
    
    csv_path = tmp_path / "test_contacts.csv"
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["email", "company", "contact_person", "notes"])
        writer.writerow(["ivanov@test.ru", "ООО Тест", "Иванов И.И.", "Примечание 1"])
        writer.writerow(["petrov@test.ru", "АО Тест2", "Петров П.П.", "Примечание 2"])
        writer.writerow(["sidorov@test.ru", "ЗАО Тест3", "Сидоров С.С.", "Примечание 3"])
    
    yield str(csv_path)


@pytest.fixture(scope="function")
def sample_xlsx_file(test_data_dir, tmp_path):
    """Создание тестового Excel файла"""
    import pandas as pd
    
    xlsx_path = tmp_path / "test_contacts.xlsx"
    
    data = {
        "email": ["test1@example.com", "test2@example.com"],
        "company": ["Компания 1", "Компания 2"],
        "contact_person": ["Контакт 1", "Контакт 2"]
    }
    
    df = pd.DataFrame(data)
    df.to_excel(xlsx_path, index=False)
    
    yield str(xlsx_path)


# Маркеры для типов тестов
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "e2e: marks end-to-end tests")
    config.addinivalue_line("markers", "slow: marks slow tests")
