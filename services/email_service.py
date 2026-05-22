"""
Сервис работы с почтой (SMTP/IMAP)
"""
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from imaplib import IMAP4_SSL
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from utils.retry import retry_with_backoff


class EmailService:
    """Сервис отправки и получения писем"""
    
    def __init__(self):
        self.smtp_server = None
        self.imap_server = None
        self.email = None
        self.password = None
    
    def configure(
        self,
        smtp_host: str,
        smtp_port: int,
        email: str,
        password: str,
        use_tls: bool = True,
        imap_host: Optional[str] = None,
        imap_port: Optional[int] = None
    ):
        """Настройка почтового аккаунта"""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.email = email
        self.password = password
        self.use_tls = use_tls
        self.imap_host = imap_host or smtp_host
        self.imap_port = imap_port or 993
        
        logger.info(f"Почтовый аккаунт настроен: {email}")
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        exceptions=(ConnectionError, smtplib.SMTPException, Exception),
    )
    def test_connection(self) -> bool:
        """Тестовое подключение"""
        try:
            # Тест SMTP
            if self.use_tls:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.email, self.password)
                    logger.info("SMTP подключение успешно")
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.email, self.password)
                    logger.info("SMTP подключение успешно (TLS)")
            
            # Тест IMAP
            with IMAP4_SSL(self.imap_host, self.imap_port) as server:
                server.login(self.email, self.password)
                logger.info("IMAP подключение успешно")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        max_delay=30.0,
        exceptions=(smtplib.SMTPException, ConnectionError, TimeoutError),
    )
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_plain: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """Отправка письма с retry"""
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg["Message-ID"] = self._generate_message_id()
            
            # Текст письма
            if body_plain:
                part_plain = MIMEText(body_plain, "plain", "utf-8")
                msg.attach(part_plain)
            
            part_html = MIMEText(body_html, "html", "utf-8")
            msg.attach(part_html)
            
            # Вложения
            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)
            
            # Отправка через SMTP с правильным выбором SSL/TLS
            if self.smtp_port == 465:
                # SSL (Gmail, некоторые другие)
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.login(self.email, self.password)
                    server.send_message(msg)
            else:
                # STARTTLS (порт 587 — Яндекс, Mail.ru и др.)
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.starttls()
                    server.login(self.email, self.password)
                    server.send_message(msg)
            
            logger.info(f"Письмо отправлено: {to_email}")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка отправки письма: {e}")
            return False
    
    def receive_emails(self, folder: str = "INBOX", limit: int = 50) -> List[Dict]:
        """Получение писем"""
        emails = []
        
        try:
            with IMAP4_SSL(self.imap_host, self.imap_port) as server:
                server.login(self.email, self.password)
                server.select(folder)
                
                # Поиск всех писем
                status, messages = server.search(None, "ALL")
                email_ids = messages[0].split()[-limit:]  # Последние limit писем
                
                for email_id in email_ids:
                    status, msg_data = server.fetch(email_id, "(RFC822)")
                    if status == "OK":
                        # Парсинг письма
                        email_dict = self._parse_email(msg_data[0][1])
                        emails.append(email_dict)
                
                logger.info(f"Получено писем: {len(emails)}")
        
        except Exception as e:
            logger.error(f"Ошибка получения писем: {e}")
        
        return emails
    
    def _generate_message_id(self) -> str:
        """Генерация Message-ID"""
        import uuid
        return f"<{uuid.uuid4()}@{self.email}>"
    
    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """Прикрепление файла"""
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                
                import os
                filename = os.path.basename(file_path)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={filename}"
                )
                msg.attach(part)
        
        except Exception as e:
            logger.error(f"Ошибка прикрепления файла: {e}")
    
    def _parse_email(self, raw_email: bytes) -> Dict:
        """Парсинг сырого письма"""
        from email import message_from_bytes
        
        msg = message_from_bytes(raw_email)
        
        return {
            "message_id": msg.get("Message-ID"),
            "from": msg.get("From"),
            "to": msg.get("To"),
            "subject": msg.get("Subject"),
            "date": msg.get("Date"),
            "body": msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        }
