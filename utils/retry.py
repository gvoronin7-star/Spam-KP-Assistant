"""
Утилита retry с экспоненциальным backoff
"""
import time
import functools
from typing import Callable, TypeVar, Optional, Tuple
from loguru import logger

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
):
    """
    Декоратор retry с экспоненциальным backoff
    
    Args:
        max_retries: Максимальное количество попыток
        base_delay: Начальная задержка (сек)
        max_delay: Максимальная задержка (сек)
        exponential_base: База экспоненты
        exceptions: Кортеж исключений для перехвата
        on_retry: Callback при retry (exception, attempt, delay)
    
    Пример:
        @retry_with_backoff(max_retries=3, exceptions=(ConnectionError,))
        def send_email(...):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt >= max_retries:
                        logger.warning(
                            f"{func.__name__}: все {max_retries} попыток исчерпаны. "
                            f"Последняя ошибка: {e}"
                        )
                        raise
                    
                    # Экспоненциальная задержка с jitter
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    logger.info(
                        f"{func.__name__}: попытка {attempt}/{max_retries} не удалась "
                        f"({e}). Повтор через {delay:.1f} сек..."
                    )
                    
                    if on_retry:
                        on_retry(e, attempt, delay)
                    
                    time.sleep(delay)
            
            # Не должно сюда дойти, но на всякий случай
            raise last_exception if last_exception else RuntimeError("Unexpected error")
        
        return wrapper
    return decorator


class RetryableOperation:
    """Класс для выполнения операций с retry"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def execute(
        self,
        operation: Callable[..., T],
        exceptions: Tuple[type, ...] = (Exception,),
        *args,
        **kwargs
    ) -> T:
        """
        Выполнить операцию с retry
        
        Args:
            operation: Функция для выполнения
            exceptions: Исключения для перехвата
            *args, **kwargs: Аргументы функции
        
        Returns:
            Результат операции
        """
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                
                if attempt >= self.max_retries:
                    logger.warning(
                        f"Операция не удалась после {self.max_retries} попыток: {e}"
                    )
                    raise
                
                delay = min(
                    self.base_delay * (self.exponential_base ** (attempt - 1)),
                    self.max_delay
                )
                
                logger.info(
                    f"Попытка {attempt}/{self.max_retries} не удалась ({e}). "
                    f"Повтор через {delay:.1f} сек..."
                )
                
                time.sleep(delay)
        
        raise last_exception if last_exception else RuntimeError("Unexpected error")
