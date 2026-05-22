"""
Тесты для AttachmentManager
"""
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from utils.attachment_manager import AttachmentManager


class TestAttachmentManager:
    """Тесты менеджера вложений"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        # Использовать временную директорию
        self.temp_dir = tempfile.mkdtemp()
        self.manager = AttachmentManager(base_dir=self.temp_dir)
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Инициализация менеджера"""
        assert self.manager.base_dir is not None
        assert self.manager.base_dir.exists()
    
    def test_ensure_base_dir(self):
        """Создание базовой директории"""
        new_dir = Path(self.temp_dir) / "new_attachments"
        manager = AttachmentManager(base_dir=str(new_dir))
        assert new_dir.exists()
    
    def test_get_dialogue_dir(self):
        """Получение директории диалога"""
        dialogue_dir = self.manager.get_dialogue_dir(123)
        
        assert dialogue_dir.exists()
        assert dialogue_dir.name == "123"
    
    def test_get_message_dir(self):
        """Получение директории сообщения"""
        message_dir = self.manager.get_message_dir(123, 456)
        
        assert message_dir.exists()
        assert message_dir.parent.name == "123"
        assert message_dir.name == "456"
    
    def test_save_attachment(self):
        """Сохранение вложения"""
        content = b"Test file content"
        filename = "test.pdf"
        
        result = self.manager.save_attachment(
            attachment_data=content,
            filename=filename,
            dialogue_id=1,
            message_id=2
        )
        
        assert result["filename"] is not None
        assert result["path"] is not None
        assert result["size"] == len(content)
        assert result["dialogue_id"] == 1
        assert result["message_id"] == 2
        
        # Проверить, что файл существует
        full_path = Path(result["full_path"])
        assert full_path.exists()
    
    def test_save_attachment_safe_filename(self):
        """Сохранение с безопасным именем файла"""
        content = b"Test"
        dangerous_filename = "test<>:|?.pdf"
        
        result = self.manager.save_attachment(
            attachment_data=content,
            filename=dangerous_filename,
            dialogue_id=1,
            message_id=2
        )
        
        # Имя должно быть изменено
        assert result["filename"] != dangerous_filename
        assert "<>" not in result["filename"]
    
    def test_save_multiple_attachments(self):
        """Сохранение нескольких вложений"""
        attachments = [
            (b"Content 1", "file1.pdf"),
            (b"Content 2", "file2.xlsx"),
            (b"Content 3", "file3.docx")
        ]
        
        results = []
        for content, filename in attachments:
            result = self.manager.save_attachment(
                attachment_data=content,
                filename=filename,
                dialogue_id=1,
                message_id=2
            )
            results.append(result)
        
        assert len(results) == 3
        
        # Все файлы должны быть в одной директории
        message_dir = self.manager.get_message_dir(1, 2)
        files = list(message_dir.iterdir())
        assert len(files) == 3
    
    def test_get_attachments_for_dialogue(self):
        """Получение вложений для диалога"""
        # Сохранить вложения
        self.manager.save_attachment(
            attachment_data=b"Content 1",
            filename="file1.pdf",
            dialogue_id=1,
            message_id=2
        )
        
        self.manager.save_attachment(
            attachment_data=b"Content 2",
            filename="file2.pdf",
            dialogue_id=1,
            message_id=3
        )
        
        # Получить вложения
        attachments = self.manager.get_attachments_for_dialogue(1)
        
        assert len(attachments) == 2
    
    def test_get_attachments_for_message(self):
        """Получение вложений для сообщения"""
        # Сохранить вложения
        self.manager.save_attachment(
            attachment_data=b"Content 1",
            filename="file1.pdf",
            dialogue_id=1,
            message_id=2
        )
        
        self.manager.save_attachment(
            attachment_data=b"Content 2",
            filename="file2.xlsx",
            dialogue_id=1,
            message_id=2
        )
        
        # Сохранить в другое сообщение
        self.manager.save_attachment(
            attachment_data=b"Content 3",
            filename="file3.docx",
            dialogue_id=1,
            message_id=4
        )
        
        # Получить вложения для сообщения 2
        attachments = self.manager.get_attachments_for_message(1, 2)
        
        assert len(attachments) == 2
    
    def test_delete_attachments_for_message(self):
        """Удаление вложений сообщения"""
        # Сохранить вложения
        self.manager.save_attachment(
            attachment_data=b"Content",
            filename="file.pdf",
            dialogue_id=1,
            message_id=2
        )
        
        # Проверить, что файл существует
        message_dir = self.manager.get_message_dir(1, 2)
        assert message_dir.exists()
        
        # Удалить
        result = self.manager.delete_attachments_for_message(1, 2)
        
        assert result is True
        
        # Директория может остаться пустой, но должна существовать
        # Проверяем, что файлов нет
        files = list(message_dir.iterdir()) if message_dir.exists() else []
        assert len(files) == 0
    
    def test_get_storage_stats(self):
        """Получение статистики хранилища"""
        # Сохранить несколько файлов
        for i in range(3):
            self.manager.save_attachment(
                attachment_data=b"X" * 1000,  # 1000 байт
                filename=f"file{i}.pdf",
                dialogue_id=1,
                message_id=i+1
            )
        
        stats = self.manager.get_storage_stats()
        
        assert stats["total_files"] == 3
        assert stats["total_size"] == 3000
        assert stats["dialogue_count"] == 1
        assert stats["total_size_mb"] == 0.0  # Меньше 1 MB
    
    def test_empty_dialogue(self):
        """Получение вложений для несуществующего диалога"""
        attachments = self.manager.get_attachments_for_dialogue(999)
        assert len(attachments) == 0
    
    def test_duplicate_filenames(self):
        """Обработка дублирующихся имён файлов"""
        # Сохранить два файла с одинаковым именем
        result1 = self.manager.save_attachment(
            attachment_data=b"Content 1",
            filename="duplicate.pdf",
            dialogue_id=1,
            message_id=2
        )
        
        result2 = self.manager.save_attachment(
            attachment_data=b"Content 2",
            filename="duplicate.pdf",
            dialogue_id=1,
            message_id=2
        )
        
        # Имена должны быть разными из-за временной метки
        assert result1["filename"] != result2["filename"]
        
        # Оба должны существовать
        assert Path(result1["full_path"]).exists()
        assert Path(result2["full_path"]).exists()


class TestAttachmentManagerIntegration:
    """Интеграционные тесты AttachmentManager"""
    
    def test_full_workflow(self):
        """Полный рабочий процесс"""
        temp_dir = tempfile.mkdtemp()
        manager = AttachmentManager(base_dir=temp_dir)
        
        try:
            # 1. Сохранить вложения для диалога
            attachments = [
                (b"KP Content", "kp_2026.pdf"),
                (b"Terms Content", "terms.docx")
            ]
            
            saved = []
            for content, filename in attachments:
                result = manager.save_attachment(
                    attachment_data=content,
                    filename=filename,
                    dialogue_id=100,
                    message_id=200
                )
                saved.append(result)
            
            # 2. Получить вложения
            retrieved = manager.get_attachments_for_message(100, 200)
            assert len(retrieved) == 2
            
            # 3. Проверить содержимое
            for att in retrieved:
                full_path = Path(att["full_path"])
                assert full_path.exists()
                
                with open(full_path, 'rb') as f:
                    content = f.read()
                assert len(content) > 0
            
            # 4. Удалить вложения
            deleted = manager.delete_attachments_for_message(100, 200)
            assert deleted is True
            
            # 5. Проверить удаление
            retrieved_after = manager.get_attachments_for_message(100, 200)
            assert len(retrieved_after) == 0
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
