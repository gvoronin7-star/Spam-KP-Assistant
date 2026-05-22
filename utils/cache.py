"""
Простой in-memory кэш с TTL
"""
import time
from typing import Optional, Any, Dict
from threading import Lock
from loguru import logger


class TTLCache:
    """
    Thread-safe кэш с временем жизни
    
    Args:
        default_ttl: Время жизни по умолчанию (сек)
        max_size: Максимальное количество записей
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._data: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            
            if time.time() > entry["expires"]:
                del self._data[key]
                return None
            
            return entry["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Сохранить значение в кэш"""
        ttl = ttl or self.default_ttl
        
        with self._lock:
            # Очистка при переполнении (LRU-like: удаляем старые)
            if len(self._data) >= self.max_size:
                self._evict_oldest()
            
            self._data[key] = {
                "value": value,
                "expires": time.time() + ttl,
                "created": time.time()
            }
    
    def delete(self, key: str):
        """Удалить ключ из кэша"""
        with self._lock:
            self._data.pop(key, None)
    
    def clear(self):
        """Очистить кэш"""
        with self._lock:
            self._data.clear()
    
    def keys(self) -> list:
        """Получить все ключи"""
        with self._lock:
            now = time.time()
            return [k for k, v in self._data.items() if v["expires"] > now]
    
    def _evict_oldest(self):
        """Удалить самую старую запись"""
        if not self._data:
            return
        oldest = min(self._data.items(), key=lambda x: x[1]["created"])
        del self._data[oldest[0]]
    
    def get_stats(self) -> Dict:
        """Статистика кэша"""
        with self._lock:
            now = time.time()
            total = len(self._data)
            expired = sum(1 for v in self._data.values() if v["expires"] <= now)
            return {
                "total_entries": total,
                "expired": expired,
                "max_size": self.max_size,
                "default_ttl": self.default_ttl
            }


# Глобальные кэши для приложения
_template_cache = TTLCache(default_ttl=600, max_size=500)   # Шаблоны — 10 мин
_profile_cache = TTLCache(default_ttl=300, max_size=200)    # Профили — 5 мин
_dialogue_cache = TTLCache(default_ttl=60, max_size=1000)   # Диалоги — 1 мин


def get_template_cache() -> TTLCache:
    """Получить кэш шаблонов"""
    return _template_cache


def get_profile_cache() -> TTLCache:
    """Получить кэш профилей"""
    return _profile_cache


def get_dialogue_cache() -> TTLCache:
    """Получить кэш диалогов"""
    return _dialogue_cache


def invalidate_cache_for_entity(entity_type: str, entity_id: Any):
    """
    Инвалидировать кэш для сущности
    
    Args:
        entity_type: 'template', 'profile', 'dialogue'
        entity_id: ID сущности
    """
    key = f"{entity_type}:{entity_id}"
    
    if entity_type == "template":
        _template_cache.delete(key)
        _template_cache.delete("templates:all")
    elif entity_type == "profile":
        _profile_cache.delete(key)
        _profile_cache.delete("profiles:all")
    elif entity_type == "dialogue":
        _dialogue_cache.delete(key)
        _dialogue_cache.delete("dialogues:all")
    
    logger.debug(f"Кэш инвалидирован: {key}")


def clear_all_caches():
    """Очистить все кэши"""
    _template_cache.clear()
    _profile_cache.clear()
    _dialogue_cache.clear()
    logger.info("Все кэши очищены")
