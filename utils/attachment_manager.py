"""
Менеджер вложений — сохранение и управление файлами из писем
"""
import os
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from loguru import logger

from utils.datetime_helper import now_utc


class AttachmentManager:
    """
    Менеджер для сохранения вложений из email
    
    Структура хранения:
    data/attachments/
    ├── {dialogue_id}/
    │   ├── {message_id}/
    │   │   ├── kp_2026-05-21.pdf
    │   │   └── document.docx
    """
    
    def __init__(self, base_dir: str = "data/attachments", max_file_size_mb: float = 50.0):
        self.base_dir = Path(base_dir)
        self.max_file_size = int(max_file_size_mb * 1024 * 1024)  # в байтах
        self._ensure_base_dir()
        logger.info(f"AttachmentManager инициализирован: {self.base_dir}, max_size={max_file_size_mb}MB")
    
    def _ensure_base_dir(self):
        """Создать базовую директорию если не существует"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Базовая директория: {self.base_dir}")
    
    def get_dialogue_dir(self, dialogue_id: int) -> Path:
        """Получить директорию для диалога"""
        dialogue_dir = self.base_dir / str(dialogue_id)
        dialogue_dir.mkdir(exist_ok=True)
        return dialogue_dir
    
    def get_message_dir(self, dialogue_id: int, message_id: int) -> Path:
        """Получить директорию для сообщения"""
        message_dir = self.get_dialogue_dir(dialogue_id) / str(message_id)
        message_dir.mkdir(exist_ok=True)
        return message_dir
    
    def save_attachment(
        self,
        attachment_data: bytes,
        filename: str,
        dialogue_id: int,
        message_id: int,
        subfolder: Optional[str] = None
    ) -> Dict:
        """
        Сохранить вложение из письма
        
        Args:
            attachment_data: Сырые данные вложения
            filename: Имя файла
            dialogue_id: ID диалога
            message_id: ID сообщения
            subfolder: Поддиректория (опционально)
        
        Returns:
            {
                "filename": "original_name.pdf",
                "path": "data/attachments/1/123/kp_2026-05-21.pdf",
                "size": 1024,
                "saved_at": "2026-05-21T12:34:56"
            }
        """
        try:
            # Проверить размер вложения
            attachment_size = len(attachment_data)
            if attachment_size > self.max_file_size:
                logger.warning(
                    f"Вложение {filename} слишком большое: "
                    f"{attachment_size / 1024 / 1024:.1f} MB > "
                    f"{self.max_file_size / 1024 / 1024:.1f} MB. Пропущено."
                )
                raise ValueError(
                    f"Файл слишком большой: {attachment_size / 1024 / 1024:.1f} MB. "
                    f"Максимум: {self.max_file_size / 1024 / 1024:.1f} MB"
                )
            
            # Генерировать безопасное имя файла
            safe_filename = self._make_safe_filename(filename)
            
            # Добавить поддиректорию если указана
            if subfolder:
                target_dir = self.get_message_dir(dialogue_id, message_id) / subfolder
            else:
                target_dir = self.get_message_dir(dialogue_id, message_id)
            
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Полный путь к файлу
            file_path = target_dir / safe_filename
            
            # Сохранить файл
            with open(file_path, 'wb') as f:
                f.write(attachment_data)
            
            # Получить размер файла
            file_size = file_path.stat().st_size
            
            # Относительный путь для хранения в БД (относительно base_dir)
            try:
                relative_path = str(file_path.relative_to(self.base_dir))
                relative_path = f"attachments/{relative_path}"  # Добавить префикс
            except ValueError:
                # Если файл вне base_dir (например, в тестах), использовать абсолютный путь
                relative_path = str(file_path)
            
            result = {
                "filename": safe_filename,
                "original_filename": filename,
                "path": relative_path,
                "full_path": str(file_path),
                "size": file_size,
                "saved_at": now_utc().isoformat(),
                "dialogue_id": dialogue_id,
                "message_id": message_id
            }
            
            logger.info(
                f"Вложение сохранено: {filename} -> {relative_path} "
                f"({file_size} байт)"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Ошибка сохранения вложения {filename}: {e}")
            raise
    
    def save_attachments_from_email(
        self,
        email_message: MIMEMultipart,
        dialogue_id: int,
        message_id: int
    ) -> List[Dict]:
        """
        Извлечь и сохранить все вложения из email.message
        
        Args:
            email_message: Объект email.message.Message
            dialogue_id: ID диалога
            message_id: ID сообщения
        
        Returns:
            Список сохранённых вложений
        """
        saved_attachments = []
        
        try:
            for part in email_message.walk():
                content_disposition = part.get("Content-Disposition")
                
                # Проверить, что это вложение
                if content_disposition and "attachment" in content_disposition:
                    filename = part.get_filename()
                    
                    if filename:
                        try:
                            # Декодировать имя файла
                            filename = self._decode_filename(filename)
                            
                            # Получить данные
                            payload = part.get_payload(decode=True)
                            
                            if payload:
                                # Сохранить
                                attachment_info = self.save_attachment(
                                    attachment_data=payload,
                                    filename=filename,
                                    dialogue_id=dialogue_id,
                                    message_id=message_id
                                )
                                
                                saved_attachments.append(attachment_info)
                        
                        except ValueError as e:
                            # Слишком большой файл — пропустить
                            logger.warning(f"Вложение пропущено: {e}")
                            continue
                        except Exception as e:
                            logger.error(f"Ошибка обработки вложения {filename}: {e}")
                            continue
            
            logger.info(
                f"Сохранено вложений для диалога {dialogue_id}, "
                f"сообщения {message_id}: {len(saved_attachments)}"
            )
        
        except Exception as e:
            logger.error(f"Ошибка извлечения вложений: {e}")
        
        return saved_attachments
    
    def _make_safe_filename(self, filename: str) -> str:
        """
        Создать безопасное имя файла
        
        - Убирает опасные символы
        - Добавляет временную метку если имя дублируется
        - Ограничивает длину
        """
        # Убрать опасные символы
        safe_name = filename
        for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            safe_name = safe_name.replace(char, '_')
        
        # Ограничить длину имени (без расширения)
        name_part = Path(safe_name).stem[:80]
        ext_part = Path(safe_name).suffix
        
        # Добавить временную метку для уникальности (с микросекундами)
        timestamp = now_utc().strftime("%Y%m%d_%H%M%S_%f")[:26]
        unique_name = f"{name_part}_{timestamp}{ext_part}"
        
        return unique_name
    
    def _decode_filename(self, filename: str) -> str:
        """Декодировать имя файла из email (если кодировано)"""
        from email.header import decode_header
        
        decoded_parts = decode_header(filename)
        result = []
        
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(charset or "utf-8", errors="ignore"))
                except:
                    result.append(part.decode("utf-8", errors="ignore"))
            else:
                result.append(part)
        
        return "".join(result)
    
    def get_attachments_for_dialogue(self, dialogue_id: int) -> List[Dict]:
        """Получить все вложения для диалога"""
        attachments = []
        dialogue_dir = self.base_dir / str(dialogue_id)
        
        if not dialogue_dir.exists():
            return attachments
        
        # Рекурсивный обход
        for file_path in dialogue_dir.rglob("*"):
            if file_path.is_file():
                # Относительный путь от base_dir
                try:
                    relative_path = f"attachments/{file_path.relative_to(self.base_dir)}"
                except ValueError:
                    relative_path = str(file_path)
                
                attachments.append({
                    "filename": file_path.name,
                    "path": relative_path,
                    "full_path": str(file_path),
                    "size": file_path.stat().st_size
                })
        
        return attachments
    
    def get_attachments_for_message(self, dialogue_id: int, message_id: int) -> List[Dict]:
        """Получить все вложения для сообщения"""
        attachments = []
        message_dir = self.get_message_dir(dialogue_id, message_id)
        
        if not message_dir.exists():
            return attachments
        
        for file_path in message_dir.iterdir():
            if file_path.is_file():
                # Относительный путь от base_dir
                try:
                    relative_path = f"attachments/{file_path.relative_to(self.base_dir)}"
                except ValueError:
                    relative_path = str(file_path)
                
                attachments.append({
                    "filename": file_path.name,
                    "path": relative_path,
                    "full_path": str(file_path),
                    "size": file_path.stat().st_size
                })
        
        return attachments
    
    def delete_attachments_for_message(self, dialogue_id: int, message_id: int) -> bool:
        """Удалить все вложения для сообщения"""
        message_dir = self.get_message_dir(dialogue_id, message_id)
        
        if not message_dir.exists():
            return False
        
        try:
            import shutil
            shutil.rmtree(message_dir)
            logger.info(f"Удалены вложения для диалога {dialogue_id}, сообщения {message_id}")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка удаления вложений: {e}")
            return False
    
    def cleanup_old_attachments(self, days: int = 30) -> int:
        """
        Очистить старые вложения (опционально)
        
        Args:
            days: Удалить вложения старше N дней
        
        Returns:
            Количество удалённых файлов
        """
        deleted_count = 0
        cutoff_date = now_utc()
        
        # Это опциональная функция, можно улучшить в будущем
        logger.info(f"Очистка старых вложений старше {days} дней (не реализовано)")
        
        return deleted_count
    
    def get_storage_stats(self) -> Dict:
        """Получить статистику хранилища вложений"""
        total_files = 0
        total_size = 0
        dialogue_count = 0
        
        if not self.base_dir.exists():
            return {
                "total_files": 0,
                "total_size": 0,
                "total_size_mb": 0,
                "dialogue_count": 0
            }
        
        dialogue_count = len([d for d in self.base_dir.iterdir() if d.is_dir()])
        
        for file_path in self.base_dir.rglob("*"):
            if file_path.is_file():
                total_files += 1
                total_size += file_path.stat().st_size
        
        return {
            "total_files": total_files,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "dialogue_count": dialogue_count
        }
