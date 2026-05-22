"""
Утилиты для работы с датами и временем.

В Python 3.12+ datetime.utcnow() deprecated.
Используем timezone-aware UTC с заменой tzinfo=None для совместимости с SQLite.
"""
from datetime import datetime, timezone


def now_utc() -> datetime:
    """
    Текущее время в UTC (naive, для совместимости с SQLite).
    
    Returns:
        datetime без tzinfo, но представляющий UTC.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def now_utc_iso() -> str:
    """Текущее время в UTC в формате ISO 8601."""
    return now_utc().isoformat()
