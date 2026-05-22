"""
Консольное приложение - альтернатива GUI
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import SessionLocal
from core.models import Profile, Contact, Template, SMTPAccount

def print_header(text):
    """Распечатать заголовок"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_menu():
    """Вывести меню"""
    print("\n[MAIN MENU]:")
    print("  1. [STATS] View statistics")
    print("  2. [PROFILES] View profiles")
    print("  3. [CONTACTS] View contacts")
    print("  4. [TEMPLATES] View templates")
    print("  5. [SMTP] View SMTP accounts")
    print("  6. [EXIT] Exit")
    print()

def show_profiles():
    """Показать профили"""
    db = SessionLocal()
    try:
        profiles = db.query(Profile).filter_by(is_active=True).all()
        print_header(f"[PROFILES] ({len(profiles)} items)")
        
        if not profiles:
            print("  No profiles found")
            return
        
        for p in profiles:
            print(f"  [{p.id}] {p.name}")
            if p.description:
                print(f"      {p.description[:60]}...")
            if p.tech_params:
                print(f"      Params: {p.tech_params}")
    finally:
        db.close()

def show_contacts():
    """Показать контакты"""
    db = SessionLocal()
    try:
        contacts = db.query(Contact).filter_by(is_active=True).all()
        print_header(f"[CONTACTS] ({len(contacts)} items)")
        
        if not contacts:
            print("  No contacts found")
            return
        
        for c in contacts:
            print(f"  [{c.id}] {c.email}")
            print(f"      Company: {c.company_name}")
            if c.contact_person:
                print(f"      Contact: {c.contact_person}")
    finally:
        db.close()

def show_templates():
    """Показать шаблоны"""
    db = SessionLocal()
    try:
        templates = db.query(Template).filter_by(is_active=True).all()
        print_header(f"[TEMPLATES] ({len(templates)} items)")
        
        if not templates:
            print("  No templates found")
            return
        
        for t in templates:
            print(f"  [{t.id}] {t.name} ({t.template_type})")
            if t.subject:
                print(f"      Subject: {t.subject}")
    finally:
        db.close()

def show_smtp_accounts():
    """Показать SMTP аккаунты"""
    db = SessionLocal()
    try:
        accounts = db.query(SMTPAccount).filter_by(is_active=True).all()
        print_header(f"[SMTP ACCOUNTS] ({len(accounts)} items)")
        
        if not accounts:
            print("  No accounts found")
            return
        
        for a in accounts:
            marker = "[*]" if a.is_primary else "[ ]"
            print(f"  [{a.id}] {marker} {a.email}")
            print(f"      SMTP: {a.smtp_server}:{a.smtp_port}")
    finally:
        db.close()

def show_stats():
    """Показать статистику"""
    db = SessionLocal()
    try:
        profiles = db.query(Profile).filter_by(is_active=True).count()
        contacts = db.query(Contact).filter_by(is_active=True).count()
        templates = db.query(Template).filter_by(is_active=True).count()
        smtp_accounts = db.query(SMTPAccount).filter_by(is_active=True).count()
        
        print_header("[STATISTICS]")
        print(f"  Profiles:       {profiles}")
        print(f"  Contacts:       {contacts}")
        print(f"  Templates:      {templates}")
        print(f"  SMTP Accounts:  {smtp_accounts}")
    finally:
        db.close()

def main():
    """Главная функция"""
    print("\n" + "="*60)
    print("  Spam KP Assistant - Console Version")
    print("  v1.0 | NLP-Core-Team")
    print("="*60)
    
    # Загрузка демо-данных при первом запуске
    from core.database import init_db
    init_db()
    
    # Проверка: есть ли данные?
    db = SessionLocal()
    profiles_count = db.query(Profile).count()
    db.close()
    
    if profiles_count == 0:
        print("\n[WARNING] No data in database!")
        print("  Run demo data script? (y/n)")
        choice = input("> ").strip().lower()
        if choice == 'y':
            import subprocess
            subprocess.run([sys.executable, "seed_demo_data.py"])
            print("\nDemo data loaded!")
    
    # Главный цикл
    while True:
        print_menu()
        choice = input("Select option (1-6): ").strip()
        
        if choice == '1':
            show_stats()
        elif choice == '2':
            show_profiles()
        elif choice == '3':
            show_contacts()
        elif choice == '4':
            show_templates()
        elif choice == '5':
            show_smtp_accounts()
        elif choice == '6':
            print("\n[GOODBYE] See you later!")
            break
        else:
            print("[ERROR] Invalid option")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
