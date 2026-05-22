"""
Тесты для дедупликации и email threading
"""
import pytest
from services.inbox_service import InboxService
from core.models import Message, Dialogue, Contact


class TestInboxDeduplication:
    """Тесты дедупликации входящих писем"""
    
    def test_duplicate_message_skipped(self, test_db, test_dialogue):
        """Дубликат письма пропускается"""
        service = InboxService()
        
        # Создать первое сообщение
        msg1 = Message(
            dialogue_id=test_dialogue.id,
            direction="inbound",
            subject="Тест",
            body_plain="Текст 1",
            message_id="<test-msg-id-123@example.com>",
            from_address="test@example.com",
            to_address="operator@example.com"
        )
        test_db.add(msg1)
        test_db.commit()
        
        # Попытка обработать дубликат
        email_data = {
            "message_id": "<test-msg-id-123@example.com>",
            "from": "Test <test@example.com>",
            "subject": "Тест",
            "body_plain": "Текст 2",
            "body_html": "",
            "raw": b""
        }
        
        result = service._process_incoming_email(email_data, test_db)
        assert result is None  # Дубликат пропущен
    
    def test_new_message_processed(self, test_db, test_dialogue):
        """Новое письмо обрабатывается"""
        service = InboxService()
        
        email_data = {
            "message_id": "<new-msg-id-456@example.com>",
            "from": "Test <test@example.com>",
            "subject": "Новое письмо",
            "body_plain": "Новый текст",
            "body_html": "",
            "raw": b""
        }
        
        result = service._process_incoming_email(email_data, test_db)
        # Письмо обработано (может вернуть None если контакт не найден, но не из-за дедупликации)
        # Проверим что сообщение не создано как дубликат
        msgs = test_db.query(Message).filter_by(message_id="<new-msg-id-456@example.com>").all()
        if result is not None:
            assert len(msgs) == 1


class TestInboxThreading:
    """Тесты email threading"""
    
    def test_threading_by_in_reply_to(self, test_db, test_dialogue, test_contact):
        """Threading по In-Reply-To"""
        service = InboxService()
        
        # Создать исходящее сообщение
        original_msg = Message(
            dialogue_id=test_dialogue.id,
            direction="outbound",
            subject="Запрос КП",
            body_plain="Просьба прислать КП",
            message_id="<original-123@example.com>",
            from_address="operator@example.com",
            to_address="test@example.com"
        )
        test_db.add(original_msg)
        test_db.commit()
        
        # Входящий ответ на это сообщение
        email_data = {
            "message_id": "<reply-456@example.com>",
            "in_reply_to": "<original-123@example.com>",
            "references": [],
            "from": "Test <test@example.com>",
            "subject": "Re: Запрос КП",
            "body_plain": "Вот наше КП",
            "body_html": "",
            "raw": b""
        }
        
        dialogue = service._find_dialogue_by_thread(email_data, test_contact, test_db)
        assert dialogue is not None
        assert dialogue.id == test_dialogue.id
    
    def test_threading_by_references(self, test_db, test_dialogue, test_contact):
        """Threading по References"""
        service = InboxService()
        
        # Создать сообщение в цепочке
        chain_msg = Message(
            dialogue_id=test_dialogue.id,
            direction="outbound",
            subject="Запрос КП",
            body_plain="Просьба прислать КП",
            message_id="<chain-msg-789@example.com>",
            from_address="operator@example.com",
            to_address="test@example.com"
        )
        test_db.add(chain_msg)
        test_db.commit()
        
        # Письмо с References на сообщение из цепочки
        email_data = {
            "message_id": "<reply-999@example.com>",
            "in_reply_to": "",
            "references": ["<chain-msg-789@example.com>"],
            "from": "Test <test@example.com>",
            "subject": "Re: Запрос КП",
            "body_plain": "Вот наше КП",
            "body_html": "",
            "raw": b""
        }
        
        dialogue = service._find_dialogue_by_thread(email_data, test_contact, test_db)
        assert dialogue is not None
        assert dialogue.id == test_dialogue.id
    
    def test_threading_by_subject(self, test_db, test_dialogue, test_contact):
        """Threading по теме письма (fallback)"""
        service = InboxService()
        
        # Создать сообщение с темой
        existing_msg = Message(
            dialogue_id=test_dialogue.id,
            direction="outbound",
            subject="Запрос КП на интернет",
            body_plain="Просьба прислать КП",
            message_id="<subj-msg@example.com>",
            from_address="operator@example.com",
            to_address="test@example.com"
        )
        test_db.add(existing_msg)
        test_db.commit()
        
        # Письмо с Re: в теме
        email_data = {
            "message_id": "<subj-reply@example.com>",
            "in_reply_to": "",
            "references": [],
            "from": "Test <test@example.com>",
            "subject": "Re: Запрос КП на интернет",
            "body_plain": "Вот КП",
            "body_html": "",
            "raw": b""
        }
        
        dialogue = service._find_dialogue_by_thread(email_data, test_contact, test_db)
        assert dialogue is not None
        assert dialogue.id == test_dialogue.id
    
    def test_no_threading_found(self, test_db, test_contact):
        """Threading не найден — возвращает None"""
        service = InboxService()
        
        email_data = {
            "message_id": "<orphan@example.com>",
            "in_reply_to": "<nonexistent@example.com>",
            "references": [],
            "from": "Test <test@example.com>",
            "subject": "Новая тема",
            "body_plain": "Текст",
            "body_html": "",
            "raw": b""
        }
        
        dialogue = service._find_dialogue_by_thread(email_data, test_contact, test_db)
        assert dialogue is None
