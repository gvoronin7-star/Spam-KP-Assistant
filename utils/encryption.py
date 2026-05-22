"""
Шифрование паролей и чувствительных данных (Fernet)
"""
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import json
import keyring
from loguru import logger

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "data"
CONFIG_DIR.mkdir(exist_ok=True)

KEYRING_SERVICE = "spam_kp_assistant"
KEYRING_USERNAME = "encryption_key"


class EncryptionManager:
    """Менеджер шифрования паролей"""
    
    _instance = None
    _fernet: Fernet = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._fernet is None:
            self._fernet = self._load_or_create_key()
    
    def _load_or_create_key(self) -> Fernet:
        """Загрузить или создать ключ шифрования"""
        try:
            # Попытка получить ключ из Windows Credential Manager
            key = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
            if key:
                logger.info("Ключ шифрования загружен из Credential Manager")
                return Fernet(key.encode())
        except Exception as e:
            logger.warning(f"Не удалось загрузить ключ из Credential Manager: {e}")
        
        # Если ключа нет, создаём новый
        logger.info("Создание нового ключа шифрования")
        fernet = Fernet.generate_key()
        
        # Сохраняем в Credential Manager
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, fernet.decode())
            logger.info("Ключ сохранён в Credential Manager")
        except Exception as e:
            logger.error(f"Не удалось сохранить ключ в Credential Manager: {e}")
            # Фолбек: сохранение в файл
            key_file = CONFIG_DIR / ".encryption_key"
            with open(key_file, "wb") as f:
                f.write(fernet)
            logger.info(f"Ключ сохранён в файл: {key_file}")
        
        return Fernet(fernet)
    
    def encrypt(self, data: str) -> str:
        """Зашифровать строку"""
        return self._fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Расшифровать строку"""
        return self._fernet.decrypt(encrypted_data.encode()).decode()
    
    def encrypt_json(self, data: dict) -> str:
        """Зашифровать JSON-объект"""
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_json(self, encrypted_data: str) -> dict:
        """Расшифровать JSON-объект"""
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)


# Глобальный экземпляр
encryption = EncryptionManager()
