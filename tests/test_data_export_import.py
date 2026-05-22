"""
Тесты для экспорта/импорта данных
"""
import json
import os
import pytest
from services.data_export_import_service import DataExportImportService
from core.models import Profile, Contact, Template


class TestDataExportImport:
    """Тесты экспорта/импорта"""
    
    def test_export_json_profiles(self, test_db, test_profile):
        """Экспорт профилей в JSON"""
        service = DataExportImportService()
        filepath = "test_export_profiles.json"
        
        result = service.export_json(test_db, filepath, entities=["profiles"])
        
        assert result["stats"]["profiles"] == 1
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert "profiles" in data
        assert len(data["profiles"]) == 1
        assert data["profiles"][0]["name"] == "Тестовый профиль"
    
        os.remove(filepath)
    
    def test_export_json_contacts(self, test_db, test_contact):
        """Экспорт контактов в JSON"""
        service = DataExportImportService()
        filepath = "test_export_contacts.json"
        
        result = service.export_json(test_db, filepath, entities=["contacts"])
        
        assert result["stats"]["contacts"] >= 1
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert "contacts" in data
        os.remove(filepath)
    
    def test_export_json_all(self, test_db, test_profile, test_contact):
        """Экспорт всех сущностей"""
        service = DataExportImportService()
        filepath = "test_export_all.json"
        
        result = service.export_json(test_db, filepath, entities=["all"])
        
        assert "profiles" in result["stats"]
        assert "contacts" in result["stats"]
        os.remove(filepath)
    
    def test_export_xml(self, test_db, test_profile):
        """Экспорт в XML"""
        service = DataExportImportService()
        filepath = "test_export_profiles.xml"
        
        result = service.export_xml(test_db, filepath, entities=["profiles"])
        
        assert result["stats"]["profiles"] == 1
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "spam_kp_export" in content
        assert "Тестовый профиль" in content
        os.remove(filepath)
    
    def test_import_json_profiles(self, test_db):
        """Импорт профилей из JSON"""
        service = DataExportImportService()
        filepath = "test_import_profiles.json"
        
        data = {
            "profiles": [
                {
                    "name": "Imported Profile",
                    "description": "Test import",
                    "is_active": True
                }
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        result = service.import_json(test_db, filepath)
        
        assert result["created"] == 1
        
        imported = test_db.query(Profile).filter_by(name="Imported Profile").first()
        assert imported is not None
        assert imported.description == "Test import"
    
        os.remove(filepath)
    
    def test_import_json_skip_existing(self, test_db, test_profile):
        """Импорт пропускает существующие без overwrite"""
        service = DataExportImportService()
        filepath = "test_import_skip.json"
        
        data = {
            "profiles": [
                {
                    "name": "Тестовый профиль",
                    "description": "Should not update",
                    "is_active": True
                }
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        result = service.import_json(test_db, filepath, overwrite=False)
        
        assert result["created"] == 0
        assert result["updated"] == 0
        os.remove(filepath)
    
    def test_import_json_overwrite(self, test_db, test_profile):
        """Импорт обновляет существующие с overwrite=True"""
        service = DataExportImportService()
        filepath = "test_import_overwrite.json"
        
        data = {
            "profiles": [
                {
                    "name": "Тестовый профиль",
                    "description": "Updated description",
                    "is_active": True
                }
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        result = service.import_json(test_db, filepath, overwrite=True)
        
        assert result["updated"] == 1
        
        updated = test_db.query(Profile).filter_by(name="Тестовый профиль").first()
        assert updated.description == "Updated description"
        os.remove(filepath)
