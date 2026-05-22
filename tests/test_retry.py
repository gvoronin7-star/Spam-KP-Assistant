"""
Тесты для utils/retry.py
"""
import pytest
from unittest.mock import MagicMock
from utils.retry import retry_with_backoff, RetryableOperation


class TestRetryWithBackoff:
    """Тесты декоратора retry"""
    
    def test_success_on_first_attempt(self):
        """Успех с первой попытки"""
        
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def operation():
            return "success"
        
        result = operation()
        assert result == "success"
    
    def test_retry_on_exception(self):
        """Retry при ошибке"""
        mock = MagicMock()
        mock.side_effect = [ConnectionError("fail 1"), ConnectionError("fail 2"), "success"]
        
        @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ConnectionError,))
        def operation():
            return mock()
        
        result = operation()
        assert result == "success"
        assert mock.call_count == 3
    
    def test_max_retries_exceeded(self):
        """Превышение max_retries"""
        mock = MagicMock()
        mock.side_effect = ConnectionError("fail")
        
        @retry_with_backoff(max_retries=2, base_delay=0.01, exceptions=(ConnectionError,))
        def operation():
            return mock()
        
        with pytest.raises(ConnectionError):
            operation()
        
        assert mock.call_count == 2
    
    def test_non_retryable_exception(self):
        """Не-перехватываемое исключение"""
        mock = MagicMock()
        mock.side_effect = ValueError("fail")
        
        @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ConnectionError,))
        def operation():
            return mock()
        
        with pytest.raises(ValueError):
            operation()
        
        assert mock.call_count == 1  # Не retry-им ValueError
    
    def test_on_retry_callback(self):
        """Callback при retry"""
        callback_mock = MagicMock()
        mock = MagicMock()
        mock.side_effect = [ConnectionError("fail"), "success"]
        
        @retry_with_backoff(
            max_retries=3,
            base_delay=0.01,
            exceptions=(ConnectionError,),
            on_retry=callback_mock
        )
        def operation():
            return mock()
        
        operation()
        
        assert callback_mock.call_count == 1
        args = callback_mock.call_args[0]
        assert isinstance(args[0], ConnectionError)
        assert args[1] == 1  # attempt
        assert args[2] == 0.01  # delay


class TestRetryableOperation:
    """Тесты класса RetryableOperation"""
    
    def test_execute_success(self):
        """Успешное выполнение"""
        op = RetryableOperation(max_retries=3, base_delay=0.01)
        
        result = op.execute(lambda: "success")
        assert result == "success"
    
    def test_execute_with_retry(self):
        """Выполнение с retry"""
        op = RetryableOperation(max_retries=3, base_delay=0.01)
        mock = MagicMock()
        mock.side_effect = [ConnectionError("fail"), "success"]
        
        result = op.execute(mock, exceptions=(ConnectionError,))
        assert result == "success"
        assert mock.call_count == 2
    
    def test_execute_max_retries(self):
        """Превышение попыток"""
        op = RetryableOperation(max_retries=2, base_delay=0.01)
        mock = MagicMock()
        mock.side_effect = ConnectionError("fail")
        
        with pytest.raises(ConnectionError):
            op.execute(mock, exceptions=(ConnectionError,))
        
        assert mock.call_count == 2
