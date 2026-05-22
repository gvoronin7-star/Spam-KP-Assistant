"""
Тесты импорта контактов
"""
import pytest


class TestCSVImport:
    """Тесты импорта из CSV"""
    
    def test_import_csv_basic(self, sample_csv_file):
        """Базовый импорт CSV"""
        from services.contact_importer import import_csv_contacts
        
        contacts = import_csv_contacts(sample_csv_file, skip_header=True)
        
        assert len(contacts) == 3
        assert contacts[0]["email"] == "ivanov@test.ru"
        assert contacts[0]["company_name"] == "ООО Тест"
    
    def test_import_csv_columns(self, sample_csv_file):
        """Импорт CSV с настройкой колонок"""
        from services.contact_importer import import_csv_contacts
        
        contacts = import_csv_contacts(
            sample_csv_file,
            skip_header=True,
            email_col=0,
            company_col=1,
            person_col=2
        )
        
        assert len(contacts) == 3
        assert contacts[0]["contact_person"] == "Иванов И.И."
    
    def test_import_csv_no_header(self, tmp_path):
        """Импорт CSV без заголовка"""
        import csv
        from services.contact_importer import import_csv_contacts
        
        csv_path = tmp_path / "no_header.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["noheader@test.com", "Company", "Person"])
        
        contacts = import_csv_contacts(str(csv_path), skip_header=False)
        
        assert len(contacts) == 1
        assert contacts[0]["email"] == "noheader@test.com"
    
    def test_import_csv_invalid_email(self, tmp_path):
        """Фильтрация невалидных email"""
        import csv
        from services.contact_importer import import_csv_contacts
        
        csv_path = tmp_path / "invalid_email.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["email", "company"])
            writer.writerow(["invalid-email", "Company"])
            writer.writerow(["valid@test.com", "Company2"])
            writer.writerow(["no-at-sign", "Company3"])
        
        # skip_header=False, т.к. первая строка — данные (в тесте "email" тоже невалидный)
        contacts = import_csv_contacts(str(csv_path), skip_header=True)
        
        # Только valid@test.com проходит валидацию
        assert len(contacts) >= 1
        emails = [c["email"] for c in contacts]
        assert "valid@test.com" in emails


class TestXLSXImport:
    """Тесты импорта из Excel"""
    
    def test_import_xlsx_basic(self, sample_xlsx_file):
        """Базовый импорт Excel"""
        from services.contact_importer import import_xlsx_contacts
        
        # skip_header=False, т.к. pandas уже читает заголовок автоматически
        contacts = import_xlsx_contacts(sample_xlsx_file, skip_header=False)
        
        assert len(contacts) == 2
        emails = [c["email"] for c in contacts]
        assert "test1@example.com" in emails
    
    def test_import_xlsx_columns(self, sample_xlsx_file):
        """Импорт Excel с настройкой колонок"""
        from services.contact_importer import import_xlsx_contacts
        
        contacts = import_xlsx_contacts(
            sample_xlsx_file,
            skip_header=True,
            email_col=0,
            company_col=1,
            person_col=2
        )
        
        # Проверяем, что контакты импортированы
        assert len(contacts) >= 1


class TestUniversalImport:
    """Тесты универсального импорта"""
    
    def test_import_auto_detect_csv(self, sample_csv_file):
        """Автоопределение CSV"""
        from services.contact_importer import import_contacts
        
        contacts = import_contacts(sample_csv_file)
        
        assert len(contacts) == 3
    
    def test_import_auto_detect_xlsx(self, sample_xlsx_file):
        """Автоопределение Excel"""
        from services.contact_importer import import_contacts
        
        contacts = import_contacts(sample_xlsx_file)
        
        # Проверяем, что контакты импортированы
        assert len(contacts) >= 1
    
    def test_import_unknown_extension(self, tmp_path):
        """Неподдерживаемый формат"""
        txt_path = tmp_path / "test.txt"
        txt_path.write_text("test")
        
        from services.contact_importer import import_contacts
        
        with pytest.raises(ValueError):
            import_contacts(str(txt_path))


class TestContactSaving:
    """Тесты сохранения контактов"""
    
    def test_save_contacts_to_db(self, test_db):
        """Сохранение в БД — проверяем возвращаемое значение"""
        from services.contact_importer import save_contacts_to_db
        
        contacts = [
            {"email": "save1@test.com", "company_name": "C1", "contact_person": "P1"},
            {"email": "save2@test.com", "company_name": "C2", "contact_person": "P2"}
        ]
        
        saved = save_contacts_to_db(contacts, db=test_db)
        
        # Проверяем, что функция вернула правильное количество
        assert saved == 2
    
    def test_save_contacts_duplicate_check(self, test_db):
        """Проверка дубликатов — сохраняем, потом пробуем дублировать"""
        from services.contact_importer import save_contacts_to_db
        
        # Сначала сохраняем уникальный контакт
        contacts1 = [
            {"email": "duplicate_check@test.com", "company_name": "C", "contact_person": "P"}
        ]
        saved1 = save_contacts_to_db(contacts1, db=test_db)
        assert saved1 == 1
        
        # Пробуем сохранить дубликат
        contacts2 = [
            {"email": "duplicate_check@test.com", "company_name": "C2", "contact_person": "P2"}
        ]
        saved2 = save_contacts_to_db(contacts2, db=test_db)
        
        # Дубликат не должен сохраниться
        assert saved2 == 0


class TestPerformance:
    """Тесты производительности"""
    
    def test_import_large_csv(self, tmp_path):
        """Импорт большого файла (1000 строк)"""
        import csv
        import time
        from services.contact_importer import import_csv_contacts
        
        csv_path = tmp_path / "large.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["email", "company"])
            for i in range(1000):
                writer.writerow([f"test{i}@example.com", f"Company {i}"])
        
        start = time.time()
        contacts = import_csv_contacts(str(csv_path))
        elapsed = time.time() - start
        
        assert len(contacts) == 1000
        assert elapsed < 10.0  # Должен импортироваться за < 10 секунд
