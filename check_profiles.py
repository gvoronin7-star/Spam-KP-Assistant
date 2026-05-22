from core.database import SessionLocal
from core.models import Profile

db = SessionLocal()
profiles = db.query(Profile).order_by(Profile.id.desc()).limit(10).all()

print('Все профили (последние 10):')
for p in profiles:
    print(f'  ID={p.id}, name={p.name}, active={p.is_active}, created={p.created_at}')

db.close()
