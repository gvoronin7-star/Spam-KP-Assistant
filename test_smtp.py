"""
SMTP Test Script
"""
import sys
sys.path.insert(0, '.')

import smtplib
from email.mime.text import MIMEText
from utils.encryption import encryption
from core.database import SessionLocal
from core.models import SMTPAccount

db = SessionLocal()
# Получаем первичный SMTP аккаунт из БД
acc = db.query(SMTPAccount).filter_by(is_primary=True).first()
if not acc:
    print("ERROR: SMTP аккаунт не найден в БД")
    print("Запустите приложение и настройте SMTP через Настройки")
    sys.exit(1)
    
pwd = encryption.decrypt(acc.password_enc)

print(f"Testing SMTP: {acc.smtp_host}:{acc.smtp_port}")
print(f"Email: {acc.email}")

try:
    # Connect
    server = smtplib.SMTP(acc.smtp_host, acc.smtp_port, timeout=10)
    server.set_debuglevel(1)
    server.starttls()
    print("Connection: OK")
    
    # Login
    server.login(acc.email, pwd)
    print("Login: OK")
    
    # Send test email
    msg = MIMEText('Test message from Spam KP Assistant')
    msg['Subject'] = 'SMTP Test'
    msg['From'] = acc.email
    msg['To'] = acc.email
    
    server.sendmail(acc.email, [acc.email], msg.as_string())
    print("Send: OK")
    
    server.quit()
    print("\nSUCCESS: All tests passed!")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    db.close()
