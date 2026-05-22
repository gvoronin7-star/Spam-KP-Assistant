"""
Тесты для utils/rate_limiter.py
"""
import time
import pytest
from utils.rate_limiter import RateLimiter, RateLimitConfig


class TestRateLimiter:
    """Тесты RateLimiter"""
    
    def test_can_make_request_initial(self):
        """Первый запрос всегда разрешён"""
        limiter = RateLimiter()
        can_request, wait, reason = limiter.can_make_request()
        
        assert can_request is True
        assert wait == 0
        assert reason == "OK"
    
    def test_rpm_limit(self):
        """Лимит запросов в минуту"""
        config = RateLimitConfig(requests_per_minute=2)
        limiter = RateLimiter(config)
        
        # Два запроса — OK
        limiter.record_request()
        limiter.record_request()
        
        # Третий — должен быть заблокирован
        can_request, wait, reason = limiter.can_make_request()
        assert can_request is False
        assert "RPM" in reason
    
    def test_wait_if_needed_blocks(self):
        """wait_if_needed возвращает False при превышении лимита"""
        config = RateLimitConfig(
            requests_per_minute=1,
            requests_per_hour=1
        )
        limiter = RateLimiter(config)
        
        limiter.record_request()
        
        # Второй запрос — должен быть отклонён
        result = limiter.wait_if_needed()
        assert result is False
    
    def test_wait_if_needed_allows(self):
        """wait_if_needed возвращает True если лимит не превышен"""
        limiter = RateLimiter()
        
        result = limiter.wait_if_needed()
        assert result is True
    
    def test_stats(self):
        """Статистика использования"""
        limiter = RateLimiter()
        limiter.record_request(tokens_used=500)
        limiter.record_request(tokens_used=300)
        
        stats = limiter.get_stats()
        
        assert stats["requests_last_minute"] == 2
        assert stats["requests_last_hour"] == 2
        assert stats["tokens_last_minute"] == 800
        assert stats["rpm_limit"] == 20
    
    def test_token_limit(self):
        """Лимит токенов в минуту"""
        config = RateLimitConfig(
            requests_per_minute=100,  # Много запросов
            tokens_per_minute=500     # Мало токенов
        )
        limiter = RateLimiter(config)
        
        limiter.record_request(tokens_used=400)
        
        # Второй запрос на 200 токенов — превысит лимит
        can_request, wait, reason = limiter.can_make_request(estimated_tokens=200)
        assert can_request is False
        assert "TPM" in reason
