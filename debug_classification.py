"""
Диагностика классификации
"""
import sys
sys.path.insert(0, '.')

from core.database import SessionLocal
from core.models import Dialogue, Message

db = SessionLocal()

try:
    print("=== ДИАГНОСТИКА КЛАССИФИКАЦИИ ===\n")
    
    # Получить все диалоги
    dialogues = db.query(Dialogue).all()
    
    for d in dialogues:
        print(f"\nДиалог ID: {d.id}")
        print(f"  Контакт: {d.contact.email}")
        print(f"  Статус: {d.status}")
        print(f"  КП получено: {d.kp_received}")
        
        # Получить входящие сообщения
        msgs = db.query(Message).filter_by(dialogue_id=d.id, direction='inbound').all()
        
        if msgs:
            for m in msgs:
                print(f"\n  Входящее сообщение:")
                print(f"    Тема: {m.subject}")
                body = m.body_plain or m.raw_body or "(пусто)"
                print(f"    Тело: {body[:150]}...")
        else:
            print("  Входящих сообщений: 0")
    
    print("\n\n=== АНАЛИЗ ===")
    print("Если в ответе 'требуется уточнить адрес' - это question, не kp_received")
    print("\nВозможные причины ошибки:")
    print("1. LLM классифицировал неверно")
    print("2. Keyword-based fallback сработал некорректно")
    print("3. В коде обработки статус не обновился")

finally:
    db.close()
