"""
Rate Limiter для API запросов
"""
import time
import threading
from typing import Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class RateLimitConfig:
    """Конфигурация rate limiting"""
    requests_per_minute: int = 20
    requests_per_hour: int = 200
    tokens_per_minute: int = 40000
    tokens_per_day: int = 500000


class RateLimiter:
    """
    Rate Limiter с поддержкой:
    - requests_per_minute
    - requests_per_hour
    - tokens_per_minute
    - tokens_per_day
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._lock = threading.Lock()
        
        # Окна для отслеживания
        self._request_times: list = []  # Времена запросов
        self._token_usage: list = []    # (time, tokens)
    
    def _clean_old(self, window_seconds: int):
        """Очистить старые записи"""
        cutoff = time.time() - window_seconds
        self._request_times = [t for t in self._request_times if t > cutoff]
        self._token_usage = [(t, c) for t, c in self._token_usage if t > cutoff]
    
    def can_make_request(self, estimated_tokens: int = 1000) -> tuple:
        """
        Проверить, можно ли сделать запрос
        
        Returns:
            (can_request: bool, wait_seconds: float, reason: str)
        """
        with self._lock:
            now = time.time()
            self._clean_old(3600)  # Очистить старше часа
            
            # Проверка requests_per_minute
            recent_requests = sum(1 for t in self._request_times if t > now - 60)
            if recent_requests >= self.config.requests_per_minute:
                wait = 60 - (now - min(t for t in self._request_times if t > now - 60))
                return False, max(0, wait), f"RPM limit ({self.config.requests_per_minute})"
            
            # Проверка requests_per_hour
            if len(self._request_times) >= self.config.requests_per_hour:
                oldest = min(self._request_times)
                wait = 3600 - (now - oldest)
                return False, max(0, wait), f"RPH limit ({self.config.requests_per_hour})"
            
            # Проверка tokens_per_minute
            recent_tokens = sum(c for t, c in self._token_usage if t > now - 60)
            if recent_tokens + estimated_tokens > self.config.tokens_per_minute:
                wait = 60 - (now - min(t for t, c in self._token_usage if t > now - 60))
                return False, max(0, wait), f"TPM limit ({self.config.tokens_per_minute})"
            
            # Проверка tokens_per_day
            day_tokens = sum(c for t, c in self._token_usage if t > now - 86400)
            if day_tokens + estimated_tokens > self.config.tokens_per_day:
                wait = 86400 - (now - min(t for t, c in self._token_usage if t > now - 86400))
                return False, max(0, wait), f"TPD limit ({self.config.tokens_per_day})"
            
            return True, 0, "OK"
    
    def record_request(self, tokens_used: int = 0):
        """Записать выполненный запрос"""
        with self._lock:
            now = time.time()
            self._request_times.append(now)
            if tokens_used > 0:
                self._token_usage.append((now, tokens_used))
            self._clean_old(86400)  # Очистить старше суток
    
    def wait_if_needed(self, estimated_tokens: int = 1000):
        """
        Подождать, если лимит исчерпан
        
        Returns:
            True если можно продолжать, False если превышен дневной лимит
        """
        can_request, wait, reason = self.can_make_request(estimated_tokens)
        
        if not can_request:
            if "TPD" in reason or "RPH" in reason:
                logger.error(f"Rate limit превышен: {reason}. Запрос отклонён.")
                return False
            
            logger.warning(
                f"Rate limit ({reason}): ожидание {wait:.1f} сек..."
            )
            time.sleep(wait + 0.5)  # Небольшой запас
            
            # Повторная проверка
            can_request, wait, reason = self.can_make_request(estimated_tokens)
            if not can_request:
                logger.error(f"Rate limit всё ещё превышен: {reason}")
                return False
        
        return True
    
    def get_stats(self) -> dict:
        """Получить статистику использования"""
        with self._lock:
            now = time.time()
            self._clean_old(86400)
            
            return {
                "requests_last_minute": sum(1 for t in self._request_times if t > now - 60),
                "requests_last_hour": len(self._request_times),
                "tokens_last_minute": sum(c for t, c in self._token_usage if t > now - 60),
                "tokens_last_day": sum(c for t, c in self._token_usage if t > now - 86400),
                "rpm_limit": self.config.requests_per_minute,
                "rph_limit": self.config.requests_per_hour,
                "tpm_limit": self.config.tokens_per_minute,
                "tpd_limit": self.config.tokens_per_day,
            }
