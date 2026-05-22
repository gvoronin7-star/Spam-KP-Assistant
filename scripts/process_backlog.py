"""
CLI-скрипт для массовой обработки накопившихся писем через LLM-агент

Примеры:
    python -m scripts.process_backlog --limit 100 --mode draft_only
    python -m scripts.process_backlog --status clarifying --auto
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from loguru import logger

from core.database import SessionLocal
from services.llm_agent_service import LLMAgentService
from core.models import Dialogue, Message


def process_backlog(
    limit: int = 100,
    mode: str = "draft_only",
    status_filter: str = "clarifying,auto_replied"
):
    """
    Обработать накопившиеся письма через LLM-агент
    
    Args:
        limit: Максимальное количество диалогов
        mode: Режим агента (draft_only, confirm, auto)
        status_filter: Статусы диалогов через запятую
    """
    db = SessionLocal()
    try:
        # Инициализация агента
        agent = LLMAgentService(mode=mode)
        
        if not agent.llm_service:
            logger.error("LLM не настроен. Установите PROXYAPI_API_KEY в .env")
            return
        
        # Парсим статусы
        statuses = [s.strip() for s in status_filter.split(",")]
        
        # Найти диалоги
        dialogues = db.query(Dialogue).filter(
            Dialogue.status.in_(statuses)
        ).order_by(Dialogue.last_activity.desc()).limit(limit).all()
        
        logger.info(f"Найдено {len(dialogues)} диалогов для обработки (режим: {mode})")
        
        stats = {"processed": 0, "drafts": 0, "sent": 0, "errors": 0, "skipped": 0}
        
        for dialogue in dialogues:
            # Получить последнее входящее
            last_message = db.query(Message).filter_by(
                dialogue_id=dialogue.id,
                direction="inbound"
            ).order_by(Message.created_at.desc()).first()
            
            if not last_message:
                continue
            
            logger.info(f"Обработка диалога {dialogue.id}: {dialogue.contact.email}")
            
            result = agent.process_incoming_message(last_message, dialogue, db)
            
            stats["processed"] += 1
            action = result.get("action", "")
            
            if action == "draft_created":
                stats["drafts"] += 1
            elif action == "sent":
                stats["sent"] += 1
            elif action == "error":
                stats["errors"] += 1
            else:
                stats["skipped"] += 1
        
        logger.info("=" * 50)
        logger.info(f"Обработка завершена:")
        logger.info(f"  Всего: {stats['processed']}")
        logger.info(f"  Черновиков: {stats['drafts']}")
        logger.info(f"  Отправлено: {stats['sent']}")
        logger.info(f"  Ошибок: {stats['errors']}")
        logger.info(f"  Пропущено: {stats['skipped']}")
        logger.info("=" * 50)
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Batch-обработка писем через LLM-агент")
    parser.add_argument("--limit", type=int, default=100, help="Максимум диалогов (default: 100)")
    parser.add_argument("--mode", type=str, default="draft_only",
                        choices=["draft_only", "confirm", "auto"],
                        help="Режим агента (default: draft_only)")
    parser.add_argument("--status", type=str, default="clarifying,auto_replied",
                        help="Статусы диалогов через запятую (default: clarifying,auto_replied)")
    parser.add_argument("--auto", action="store_true",
                        help="Автоматический режим (mode=auto)")
    
    args = parser.parse_args()
    
    mode = "auto" if args.auto else args.mode
    
    process_backlog(
        limit=args.limit,
        mode=mode,
        status_filter=args.status
    )


if __name__ == "__main__":
    main()
