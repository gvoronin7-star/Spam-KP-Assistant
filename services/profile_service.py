"""
Сервис профилей с кэшированием
"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from loguru import logger

from core.models import Profile
from utils.cache import get_profile_cache, invalidate_cache_for_entity


class ProfileService:
    """Сервис для работы с профилями (с кэшированием)"""
    
    def __init__(self):
        self.cache = get_profile_cache()
    
    def get_by_id(self, profile_id: int, db: Session) -> Optional[Profile]:
        """Получить профиль по ID (с кэшем)"""
        cache_key = f"profile:{profile_id}"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        profile = db.query(Profile).filter_by(id=profile_id).first()
        if profile:
            self.cache.set(cache_key, profile)
        
        return profile
    
    def get_all_active(self, db: Session) -> List[Profile]:
        """Получить все активные профили (с кэшем)"""
        cache_key = "profiles:all"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        profiles = db.query(Profile).filter_by(is_active=True).all()
        self.cache.set(cache_key, profiles, ttl=300)
        return profiles
    
    def create(self, profile_data: Dict, db: Session) -> Profile:
        """Создать профиль"""
        profile = Profile(**profile_data)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        self.cache.delete("profiles:all")
        
        logger.info(f"Создан профиль: {profile.name}")
        return profile
    
    def update(self, profile_id: int, profile_data: Dict, db: Session) -> Optional[Profile]:
        """Обновить профиль"""
        profile = db.query(Profile).filter_by(id=profile_id).first()
        if not profile:
            return None
        
        for key, value in profile_data.items():
            setattr(profile, key, value)
        
        db.commit()
        db.refresh(profile)
        
        invalidate_cache_for_entity("profile", profile_id)
        
        logger.info(f"Обновлён профиль: {profile.name}")
        return profile
    
    def delete(self, profile_id: int, db: Session) -> bool:
        """Деактивировать профиль"""
        profile = db.query(Profile).filter_by(id=profile_id).first()
        if not profile:
            return False
        
        profile.is_active = False
        db.commit()
        
        invalidate_cache_for_entity("profile", profile_id)
        
        logger.info(f"Деактивирован профиль: {profile.name}")
        return True
