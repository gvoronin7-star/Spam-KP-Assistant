"""
Конфигурация приложения
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path

# Определение корня проекта
PROJECT_ROOT = Path(__file__).parent

# Загрузка версии из файла VERSION
try:
    VERSION_FILE = PROJECT_ROOT / "VERSION"
    if VERSION_FILE.exists():
        __version__ = VERSION_FILE.read_text(encoding="utf-8").strip()
    else:
        __version__ = "2.1.0"  # Fallback
except Exception:
    __version__ = "2.1.0"  # Fallback

class Settings(BaseSettings):
    """Настройки приложения"""
    
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        case_sensitive=False,
        extra="ignore"
    )
    
    # ProxyAPI
    proxyapi_api_key: Optional[str] = None
    proxyapi_primary_model: str = "gpt-5.4-mini"
    proxyapi_fallback_model: str = "gpt-5.3-chat-latest"
    proxyapi_parsing_model: str = "gemini-3.1-flash-lite"
    
    # LLM Agent
    llm_agent_mode: str = "draft_only"  # disabled, draft_only, confirm, auto
    llm_agent_auto_reply_categories: str = "question,auto_reply"  # через запятую
    llm_agent_min_confidence: float = 0.6  # минимальная уверенность для автоответа
    llm_agent_max_daily_auto_replies: int = 50  # лимит автоответов в день
    
    # База данных
    database_url: str = "sqlite:///data/spam_kp_assistant.db"
    
    # Логирование
    log_level: str = "INFO"
    log_file: str = "data/app.log"
    
    # Почта (по умолчанию)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_use_tls: bool = True
    
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_use_ssl: bool = True
    
    # Интерфейс
    window_width: int = 1200
    window_height: int = 800
    
    # Планировщик
    auto_check_email_enabled: bool = True
    email_check_interval_hours: int = 1
    reminder_check_interval_minutes: int = 30
    daily_cleanup_hour: int = 2
    daily_cleanup_minute: int = 0
    

# Глобальный экземпляр
settings = Settings()
