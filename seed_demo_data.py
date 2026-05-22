"""
Заполнение БД демонстрационными данными
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import SessionLocal, init_db
from core.models import Profile, Contact, Template, SMTPAccount

# Прямой импорт без через utils/__init__.py
from utils.encryption import EncryptionManager

encryption = EncryptionManager()


def seed_demo_data():
    """Заполнение БД демо-данными"""
    print("=" * 60)
    print("  Заполнение БД демонстрационными данными")
    print("=" * 60)
    print()
    
    # Инициализация БД
    init_db()
    
    db = SessionLocal()
    created = 0
    
    try:
        # 1. Профили (3 шт)
        print("[1/4] Создание профилей...")
        
        profiles = [
            {
                "name": "Интернет-канал 100 Мбит/с",
                "description": "Запрос КП на подключение интернет-канала 100 Мбит/с для офиса",
                "tech_params": {
                    "speed": "100 Мбит/с",
                    "protocol": "Ethernet",
                    "sla": "99.9%"
                },
                "requirements": {
                    "price": True,
                    "term": True,
                    "equipment": True
                },
                "dialogue_rules": {
                    "qa_pairs": [
                        {"question": "Сколько стоит?", "answer": "Укажите стоимость подключения и абонплату"},
                        {"question": "Сроки?", "answer": "Укажите сроки подключения"}
                    ]
                },
                "attachments": [],
                "is_active": True
            },
            {
                "name": "Виртуальная АТС на 50 номеров",
                "description": "Запрос КП на развертывание Виртуальной АТС для call-центра",
                "tech_params": {
                    "simultaneous_calls": "20 каналов",
                    "recording": True,
                    "ivr": True
                },
                "requirements": {
                    "price": True,
                    "term": True,
                    "integration": True
                },
                "dialogue_rules": {
                    "qa_pairs": [
                        {"question": "Функции?", "answer": "Укажите список функций АТС"},
                        {"question": "Цена?", "answer": "Укажите стоимость установки и абонплату"}
                    ]
                },
                "attachments": [],
                "is_active": True
            },
            {
                "name": "Выделенная линия 1 Гбит/с",
                "description": "Запрос КП на аренду выделенной линии для ЦОД",
                "tech_params": {
                    "speed": "1 Гбит/с",
                    "protocol": "Optical",
                    "redundancy": "Dual-homing"
                },
                "requirements": {
                    "price": True,
                    "term": True,
                    "sla": True
                },
                "dialogue_rules": {
                    "qa_pairs": [
                        {"question": "SLA?", "answer": "Укажите уровень SLA"},
                        {"question": "Стоимость?", "answer": "Укажите ежемесячную стоимость"}
                    ]
                },
                "attachments": [],
                "is_active": True
            }
        ]
        
        for p in profiles:
            profile = Profile(**p)
            db.add(profile)
            created += 1
        
        db.commit()
        print(f"      Создано профилей: {len(profiles)}")
        
        # 2. Контакты (5 шт)
        print("[2/4] Создание контактов...")
        
        contacts = [
            {
                "email": "sales@telecom.ru",
                "company_name": "ООО Телеком",
                "contact_person": "Иванов Иван Иванович",
                "notes": "Основной поставщик, работает с 2015 года",
                "profile_id": None,
                "is_active": True
            },
            {
                "email": "info@netgroup.ru",
                "company_name": "АО НетГрупп",
                "contact_person": "Петрова Анна Сергеевна",
                "notes": "Региональный представитель",
                "profile_id": None,
                "is_active": True
            },
            {
                "email": "kp@biznet.ru",
                "company_name": "БИЗНЕТ Связь",
                "contact_person": "Сидоров Петр Ильич",
                "notes": "Федеральный оператор",
                "profile_id": None,
                "is_active": True
            },
            {
                "email": "sales@rtcomm.ru",
                "company_name": "РТКомм.РУ",
                "contact_person": "Кузнецов Алексей Владимирович",
                "notes": "Провайдер в Москве и МО",
                "profile_id": None,
                "is_active": True
            },
            {
                "email": "b2b@akado.ru",
                "company_name": "АкАДО",
                "contact_person": "Новикова Елена Дмитриевна",
                "notes": "Кабельный оператор",
                "profile_id": None,
                "is_active": True
            }
        ]
        
        for c in contacts:
            contact = Contact(**c)
            db.add(contact)
            created += 1
        
        db.commit()
        print(f"      Создано контактов: {len(contacts)}")
        
        # 3. Шаблоны (3 шт)
        print("[3/4] Создание шаблонов...")
        
        templates = [
            {
                "name": "Первичный запрос КП",
                "template_type": "initial",
                "subject": "Запрос коммерческого предложения - {{ service_name }}",
                "body_plain": """Добрый день, {{ contact_person }}!

Наша компания {{ operator_name }} запрашивает коммерческое предложение на:

{{ service_name }}

Просим предоставить:
1. Стоимость подключения
2. Размер ежемесячной абонентской платы
3. Сроки подключения
4. Необходимое оборудование

Также просим указать:
- Условия договора
- Гарантии качества
- Техподдержку

Дата запроса: {{ request_date }}

Заранее благодарим за ответ!

С уважением,
{{ operator_name }}
""",
                "body_html": """<html>
<body style="font-family: Arial, sans-serif;">
<h2>Запрос коммерческого предложения</h2>
<p>Добрый день, <b>{{ contact_person }}</b>!</p>
<p>Наша компания <b>{{ operator_name }}</b> запрашивает коммерческое предложение на:</p>
<h3>{{ service_name }}</h3>
<p><b>Просим предоставить:</b></p>
<ol>
  <li>Стоимость подключения</li>
  <li>Размер ежемесячной абонентской платы</li>
  <li>Сроки подключения</li>
  <li>Необходимое оборудование</li>
</ol>
<p><b>Также просим указать:</b></p>
<ul>
  <li>Условия договора</li>
  <li>Гарантии качества</li>
  <li>Техподдержку</li>
</ul>
<p><i>Дата запроса: {{ request_date }}</i></p>
<p>Заранее благодарим за ответ!</p>
<p>С уважением,<br>
<b>{{ operator_name }}</b></p>
</body>
</html>""",
                "attachments": [],
                "version": 1,
                "is_active": True
            },
            {
                "name": "Напоминание 1",
                "template_type": "reminder",
                "subject": "Напоминание: Запрос КП - {{ service_name }}",
                "body_plain": """Добрый день, {{ contact_person }}!

Напоминаем о нашем запросе коммерческого предложения от {{ request_date }}:

{{ service_name }}

До настоящего времени мы не получили ответа.

Просим вас оперативно предоставить КП или сообщить о невозможности сотрудничества.

Заранее благодарим!

С уважением,
{{ operator_name }}
""",
                "body_html": """<html>
<body style="font-family: Arial, sans-serif;">
<h2>Напоминание о запросе КП</h2>
<p>Добрый день, <b>{{ contact_person }}</b>!</p>
<p>Напоминаем о нашем запросе коммерческого предложения от <b>{{ request_date }}</b>:</p>
<h3>{{ service_name }}</h3>
<p>До настоящего времени мы не получили ответа.</p>
<p><b>Просим вас оперативно предоставить КП</b> или сообщить о невозможности сотрудничества.</p>
<p>Заранее благодарим!</p>
<p>С уважением,<br>
<b>{{ operator_name }}</b></p>
</body>
</html>""",
                "attachments": [],
                "version": 1,
                "is_active": True
            },
            {
                "name": "Уточнение условий",
                "template_type": "followup",
                "subject": "Уточнение по КП - {{ service_name }}",
                "body_plain": """Добрый день, {{ contact_person }}!

Спасибо за предоставленное коммерческое предложение.

Просим уточнить следующие моменты:
1. [указать вопрос 1]
2. [указать вопрос 2]
3. [указать вопрос 3]

Также просим подтвердить актуальность цен на срок до [дата].

Ждем вашего ответа!

С уважением,
{{ operator_name }}
""",
                "body_html": """<html>
<body style="font-family: Arial, sans-serif;">
<h2>Уточнение по КП</h2>
<p>Добрый день, <b>{{ contact_person }}</b>!</p>
<p>Спасибо за предоставленное коммерческое предложение.</p>
<p><b>Просим уточнить следующие моменты:</b></p>
<ol>
  <li>[указать вопрос 1]</li>
  <li>[указать вопрос 2]</li>
  <li>[указать вопрос 3]</li>
</ol>
<p>Также просим подтвердить актуальность цен на срок до <b>[дата]</b>.</p>
<p>Ждем вашего ответа!</p>
<p>С уважением,<br>
<b>{{ operator_name }}</b></p>
</body>
</html>""",
                "attachments": [],
                "version": 1,
                "is_active": True
            }
        ]
        
        for t in templates:
            template = Template(**t)
            db.add(template)
            created += 1
        
        db.commit()
        print(f"      Создано шаблонов: {len(templates)}")
        
        # 4. SMTP аккаунт (демо)
        print("[4/4] Создание демо SMTP аккаунта...")
        
        smtp_account = SMTPAccount(
            name="Демо аккаунт",
            email="demo@example.com",
            smtp_host="smtp.example.com",
            smtp_port=465,
            imap_host="imap.example.com",
            imap_port=993,
            smtp_use_tls=True,
            imap_use_ssl=True,
            login="demo@example.com",
            password_enc=encryption.encrypt("demo_password"),
            is_primary=True,
            is_active=False  # Отключён, т.к. демо
        )
        
        db.add(smtp_account)
        db.commit()
        created += 1
        
        print(f"      Создан демо SMTP аккаунт")
        
        print()
        print("=" * 60)
        print(f"  УСПЕШНО! Создано объектов: {created}")
        print("=" * 60)
        print()
        print("Теперь в приложении вы увидите:")
        print("  - 3 профиля закупок")
        print("  - 5 контактов поставщиков")
        print("  - 3 шаблона писем")
        print("  - 1 демо SMTP аккаунт (отключён)")
        print()
        
        return True
    
    except Exception as e:
        db.rollback()
        print(f"      ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
