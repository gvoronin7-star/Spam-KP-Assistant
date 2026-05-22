"""
Менеджер SMTP/IMAP аккаунтов
"""
import smtplib
from imaplib import IMAP4_SSL
from typing import Dict, Optional, Tuple
from loguru import logger
from utils.encryption import encryption


class SMTPManager:
    """Менеджер SMTP/IMAP аккаунтов"""
    
    def __init__(self):
        self.accounts = {}
    
    def test_smtp_connection(
        self,
        smtp_host: str,
        smtp_port: int,
        email: str,
        password: str,
        use_tls: bool = True
    ) -> Tuple[bool, str]:
        """
        Тестирование SMTP подключения
        
        Returns:
            (успех, сообщение)
        """
        try:
            if use_tls:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                    server.login(email, password)
                    server.quit()
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(email, password)
                    server.quit()
            
            logger.info(f"SMTP подключение успешно: {email}")
            return True, "SMTP подключение успешно"
        
        except smtplib.SMTPAuthenticationError:
            logger.error(f"Ошибка аутентификации SMTP: {email}")
            return False, "Ошибка аутентификации (неверный логин/пароль)"
        
        except smtplib.SMTPConnectError:
            logger.error(f"Не удалось подключиться к SMTP: {smtp_host}:{smtp_port}")
            return False, f"Не удалось подключиться к {smtp_host}:{smtp_port}"
        
        except Exception as e:
            logger.error(f"Ошибка SMTP: {e}")
            return False, f"Ошибка: {str(e)}"
    
    def test_imap_connection(
        self,
        imap_host: str,
        imap_port: int,
        email: str,
        password: str,
        use_ssl: bool = True
    ) -> Tuple[bool, str]:
        """
        Тестирование IMAP подключения
        
        Returns:
            (успех, сообщение)
        """
        try:
            if use_ssl:
                with IMAP4_SSL(imap_host, imap_port, timeout=10) as server:
                    server.login(email, password)
                    server.select('INBOX')
                    server.logout()
            else:
                with IMAP4_SSL(imap_host, imap_port, timeout=10) as server:
                    server.login(email, password)
                    server.select('INBOX')
                    server.logout()
            
            logger.info(f"IMAP подключение успешно: {email}")
            return True, "IMAP подключение успешно"
        
        except smtplib.SMTPAuthenticationError:
            logger.error(f"Ошибка аутентификации IMAP: {email}")
            return False, "Ошибка аутентификации (неверный логин/пароль)"
        
        except Exception as e:
            logger.error(f"Ошибка IMAP: {e}")
            return False, f"Ошибка: {str(e)}"
    
    def test_full_connection(
        self,
        smtp_host: str,
        smtp_port: int,
        imap_host: str,
        imap_port: int,
        email: str,
        password: str,
        use_tls: bool = True,
        use_ssl: bool = True
    ) -> Dict:
        """
        Полное тестирование SMTP и IMAP
        
        Returns:
            {
                'smtp_success': bool,
                'smtp_message': str,
                'imap_success': bool,
                'imap_message': str,
                'overall_success': bool
            }
        """
        smtp_success, smtp_msg = self.test_smtp_connection(
            smtp_host, smtp_port, email, password, use_tls
        )
        
        imap_success, imap_msg = self.test_imap_connection(
            imap_host, imap_port, email, password, use_ssl
        )
        
        return {
            'smtp_success': smtp_success,
            'smtp_message': smtp_msg,
            'imap_success': imap_success,
            'imap_message': imap_msg,
            'overall_success': smtp_success and imap_success
        }
    
    def save_account(
        self,
        name: str,
        email: str,
        smtp_host: str,
        smtp_port: int,
        imap_host: str,
        imap_port: int,
        login: str,
        password: str,
        use_tls: bool = True,
        use_ssl: bool = True,
        is_primary: bool = False
    ) -> int:
        """
        Сохранение аккаунта в БД
        
        Returns:
            ID аккаунта
        """
        from core.database import SessionLocal
        from core.models import SMTPAccount
        
        db = SessionLocal()
        
        try:
            # Если основной, снять флаг с других
            if is_primary:
                db.query(SMTPAccount).filter_by(is_primary=True).update({"is_primary": False})
            
            # Шифрование пароля
            password_enc = encryption.encrypt(password)
            
            # Проверка是否存在
            existing = db.query(SMTPAccount).filter_by(email=email).first()
            
            if existing:
                # Обновление
                existing.name = name
                existing.smtp_host = smtp_host
                existing.smtp_port = smtp_port
                existing.imap_host = imap_host
                existing.imap_port = imap_port
                existing.smtp_use_tls = use_tls
                existing.imap_use_ssl = use_ssl
                existing.login = login
                existing.password_enc = password_enc
                existing.is_primary = is_primary
                existing.is_active = True
                
                account_id = existing.id
                action = "обновлён"
            else:
                # Создание
                account = SMTPAccount(
                    name=name,
                    email=email,
                    smtp_host=smtp_host,
                    smtp_port=smtp_port,
                    imap_host=imap_host,
                    imap_port=imap_port,
                    smtp_use_tls=use_tls,
                    imap_use_ssl=use_ssl,
                    login=login,
                    password_enc=password_enc,
                    is_primary=is_primary,
                    is_active=True
                )
                
                db.add(account)
                db.commit()
                db.refresh(account)
                
                account_id = account.id
                action = "создан"
            
            logger.info(f"SMTP аккаунт {action}: ID={account_id}, email={email}")
            
            return account_id
        
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка сохранения аккаунта: {e}")
            raise
        
        finally:
            db.close()
    
    def get_accounts(self):
        """Получение всех аккаунтов"""
        from core.database import SessionLocal
        from core.models import SMTPAccount
        
        db = SessionLocal()
        
        try:
            accounts = db.query(SMTPAccount).all()
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "email": a.email,
                    "is_primary": a.is_primary,
                    "is_active": a.is_active,
                    "last_check": a.last_check,
                    "last_error": a.last_error
                }
                for a in accounts
            ]
        finally:
            db.close()
    
    def get_primary_account(self):
        """Получение основного аккаунта"""
        from core.database import SessionLocal
        from core.models import SMTPAccount
        
        db = SessionLocal()
        
        try:
            account = db.query(SMTPAccount).filter_by(
                is_primary=True,
                is_active=True
            ).first()
            
            if account:
                return {
                    "id": account.id,
                    "email": account.email,
                    "smtp_host": account.smtp_host,
                    "smtp_port": account.smtp_port,
                    "imap_host": account.imap_host,
                    "imap_port": account.imap_port,
                    "smtp_use_tls": account.smtp_use_tls,
                    "imap_use_ssl": account.imap_use_ssl,
                    "login": account.login,
                    "password": encryption.decrypt(account.password_enc)
                }
            return None
        finally:
            db.close()
