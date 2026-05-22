"""
Исправление статусов диалогов
"""
import sys
sys.path.insert(0, '.')

from core.database import SessionLocal
from core.models import Dialogue, Message

db = SessionLocal()

try:
    print("=== ИСПРАВЛЕНИЕ СТАТУСОВ ===\n")
    
    # Найти диалоги с неправильным статусом
    dialogues = db.query(Dialogue).filter_by(kp_received=True).all()
    
    for d in dialogues:
        # Проверить, есть ли вопросы в последнем сообщении
        msgs = db.query(Message).filter_by(dialogue_id=d.id, direction='inbound').order_by(Message.created_at.desc()).all()
        
        if msgs:
            last_msg = msgs[0]
            body = (last_msg.body_plain or "").lower()
            subject = (last_msg.subject or "").lower()
            
            # Проверить на вопросы
            has_questions = any(word in body for word in [
                'уточнить', 'вопрос', 'какой', 'где', 'когда', 'сколько',
                'нужно', 'необходимо', 'просьба', 'please', '?'
            ])
            
            has_kp = any(word in body for word in [
                'коммерческое предложение', 'кп прилагается', 'во вложении',
                'цена', 'стоимость', 'тариф', 'прайс'
            ])
            
            print(f"Диалог: {d.contact.email}")
            print(f"  Текущий статус: {d.status}")
            print(f"  Вопросы: {has_questions}, КП: {has_kp}")
            
            # Если есть вопросы и нет КП — исправить статус
            if has_questions and not has_kp:
                d.status = 'clarifying'
                d.kp_received = False
                print(f"  FIXED to: {d.status}")
            else:
                print(f"  KEPT: {d.status}")
            print()
    
    db.commit()
    print("\nГотово!")

finally:
    db.close()
