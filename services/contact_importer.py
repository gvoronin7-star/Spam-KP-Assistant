"""
Сервис импорта контактов
"""
import csv
from pathlib import Path
from typing import List, Dict
from loguru import logger


def import_csv_contacts(
    file_path: str,
    skip_header: bool = True,
    email_col: int = 0,
    company_col: int = 1,
    person_col: int = 2
) -> List[Dict]:
    """
    Импорт контактов из CSV
    
    Args:
        file_path: Путь к CSV файлу
        skip_header: Пропускать ли первую строку
        email_col: Номер колонки с email (0-based)
        company_col: Номер колонки с названием компании
        person_col: Номер колонки с именем контакта
    
    Returns:
        Список словарей с контактами
    """
    contacts = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            
            # Пропуск заголовка
            if skip_header:
                next(reader, None)
            
            for row in reader:
                if len(row) > email_col:
                    email = row[email_col].strip()
                    
                    # Валидация email
                    if email and '@' in email:
                        contact = {
                            "email": email,
                            "company_name": row[company_col].strip() if company_col < len(row) else "",
                            "contact_person": row[person_col].strip() if person_col < len(row) else "",
                            "notes": ""
                        }
                        contacts.append(contact)
        
        logger.info(f"Импортировано из CSV: {len(contacts)} контактов")
    
    except Exception as e:
        logger.error(f"Ошибка импорта CSV: {e}")
        raise
    
    return contacts


def import_xlsx_contacts(
    file_path: str,
    skip_header: bool = True,
    email_col: int = 0,
    company_col: int = 1,
    person_col: int = 2
) -> List[Dict]:
    """
    Импорт контактов из Excel (XLSX)
    
    Args:
        file_path: Путь к Excel файлу
        skip_header: Пропускать ли первую строку
        email_col: Номер колонки с email (0-based)
        company_col: Номер колонки с названием компании
        person_col: Номер колонки с именем контакта
    
    Returns:
        Список словарей с контактами
    """
    contacts = []
    
    try:
        import pandas as pd
        
        df = pd.read_excel(file_path)
        
        # Пропуск заголовка
        if skip_header:
            df = df.iloc[1:]
        
        for idx, row in df.iterrows():
            try:
                email = str(row.iloc[email_col]).strip()
                
                if email and '@' in email:
                    contact = {
                        "email": email,
                        "company_name": str(row.iloc[company_col]).strip() if company_col < len(row) else "",
                        "contact_person": str(row.iloc[person_col]).strip() if person_col < len(row) else "",
                        "notes": ""
                    }
                    contacts.append(contact)
            
            except Exception as e:
                logger.warning(f"Пропущена строка {idx}: {e}")
                continue
        
        logger.info(f"Импортировано из Excel: {len(contacts)} контактов")
    
    except Exception as e:
        logger.error(f"Ошибка импорта Excel: {e}")
        raise
    
    return contacts


def import_contacts(
    file_path: str,
    skip_header: bool = True,
    email_col: int = 0,
    company_col: int = 1,
    person_col: int = 2
) -> List[Dict]:
    """
    Универсальный импорт контактов (автоопределение формата)
    
    Args:
        file_path: Путь к файлу
        skip_header: Пропускать ли первую строку
        email_col: Номер колонки с email
        company_col: Номер колонки с компанией
        person_col: Номер колонки с контактным лицом
    
    Returns:
        Список словарей с контактами
    """
    ext = Path(file_path).suffix.lower()
    
    if ext == '.csv':
        return import_csv_contacts(file_path, skip_header, email_col, company_col, person_col)
    elif ext in ['.xlsx', '.xls']:
        return import_xlsx_contacts(file_path, skip_header, email_col, company_col, person_col)
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {ext}")


def save_contacts_to_db(contacts: List[Dict], profile_id: int = None, db=None):
    """
    Сохранение импортированных контактов в БД
    
    Args:
        contacts: Список контактов
        profile_id: ID профиля (опционально)
        db: Сессия БД (опционально, для тестирования)
    """
    from core.database import SessionLocal
    from core.models import Contact
    
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    
    saved = 0
    
    try:
        for contact_data in contacts:
            # Проверка на дубликаты
            existing = db.query(Contact).filter(
                Contact.email == contact_data["email"]
            ).first()
            
            if existing:
                logger.warning(f"Пропущен дубликат: {contact_data['email']}")
                continue
            
            contact = Contact(
                email=contact_data["email"],
                company_name=contact_data.get("company_name", ""),
                contact_person=contact_data.get("contact_person", ""),
                notes=contact_data.get("notes", ""),
                profile_id=profile_id,
                is_active=True
            )
            
            db.add(contact)
            saved += 1
        
        db.commit()
        logger.info(f"Сохранено {saved} контактов в БД")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка сохранения контактов: {e}")
        raise
    
    finally:
        if close_db:
            db.close()
    
    return saved
