"""
Тесты для TTL Cache
"""
import time
import pytest
from utils.cache import TTLCache, get_template_cache, get_profile_cache, invalidate_cache_for_entity, clear_all_caches


class TestTTLCache:
    """Тесты TTL кэша"""
    
    def test_get_set(self):
        """Базовое сохранение и получение"""
        cache = TTLCache(default_ttl=60)
        cache.set("key1", "value1")
        
        assert cache.get("key1") == "value1"
    
    def test_get_missing_returns_none(self):
        """Отсутствующий ключ возвращает None"""
        cache = TTLCache(default_ttl=60)
        assert cache.get("missing") is None
    
    def test_ttl_expiration(self):
        """Истечение TTL"""
        cache = TTLCache(default_ttl=1)
        cache.set("key", "value")
        
        assert cache.get("key") == "value"
        time.sleep(1.1)
        assert cache.get("key") is None
    
    def test_delete(self):
        """Удаление ключа"""
        cache = TTLCache(default_ttl=60)
        cache.set("key", "value")
        cache.delete("key")
        
        assert cache.get("key") is None
    
    def test_clear(self):
        """Очистка кэша"""
        cache = TTLCache(default_ttl=60)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        
        assert cache.get("k1") is None
        assert cache.get("k2") is None
    
    def test_max_size_eviction(self):
        """Вытеснение при переполнении"""
        cache = TTLCache(default_ttl=60, max_size=2)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")  # Должно вытеснить k1
        
        assert cache.get("k1") is None
        assert cache.get("k2") == "v2"
        assert cache.get("k3") == "v3"
    
    def test_stats(self):
        """Статистика кэша"""
        cache = TTLCache(default_ttl=60, max_size=10)
        cache.set("k1", "v1")
        
        stats = cache.get_stats()
        assert stats["total_entries"] == 1
        assert stats["max_size"] == 10
    
    def test_custom_ttl(self):
        """Пользовательский TTL"""
        cache = TTLCache(default_ttl=60)
        cache.set("short", "value", ttl=1)
        
        assert cache.get("short") == "value"
        time.sleep(1.1)
        assert cache.get("short") is None


class TestGlobalCaches:
    """Тесты глобальных кэшей"""
    
    def test_template_cache(self):
        """Кэш шаблонов"""
        cache = get_template_cache()
        cache.set("template:1", {"name": "Test"})
        
        assert cache.get("template:1") == {"name": "Test"}
    
    def test_profile_cache(self):
        """Кэш профилей"""
        cache = get_profile_cache()
        cache.set("profile:1", {"name": "Profile"})
        
        assert cache.get("profile:1") == {"name": "Profile"}
    
    def test_invalidate_entity(self):
        """Инвалидация по сущности"""
        cache = get_template_cache()
        cache.set("template:5", {"name": "T"})
        cache.set("templates:all", [])
        
        invalidate_cache_for_entity("template", 5)
        
        assert cache.get("template:5") is None
        assert cache.get("templates:all") is None
    
    def test_clear_all(self):
        """Очистка всех кэшей"""
        get_template_cache().set("a", 1)
        get_profile_cache().set("b", 2)
        
        clear_all_caches()
        
        assert get_template_cache().get("a") is None
        assert get_profile_cache().get("b") is None
