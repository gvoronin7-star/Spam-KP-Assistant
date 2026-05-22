"""
Сервис планировщика для фоновых задач
"""
from datetime import datetime
from typing import Optional, Callable, Dict
from loguru import logger

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler не установлен. Фоновые задачи не будут работать.")


class SchedulerService:
    """
    Сервис планировщика на базе APScheduler
    
    Функции:
    - Фоновая проверка почты каждый час
    - Отправка запланированных напоминаний
    - Регулярная синхронизация статусов
    
    Для работы требуется APScheduler:
    pip install APScheduler
    """
    
    def __init__(self):
        self._running = False
        self._jobs = {}
        
        if not APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler недоступен. Планировщик не будет работать.")
            self.scheduler = None
            return
        
        # Настройка хранилища заданий в БД
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
        }
        
        # Создаем планировщик
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            job_defaults={
                'coalesce': True,  # Объединять пропущенные выполнения
                'max_instances': 3,  # Максимум 3 параллельных выполнения
                'misfire_grace_time': 3600  # 1 час на догоняние
            }
        )
        
        # Обработчики событий
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
        
        logger.info("SchedulerService инициализирован")
    
    def start(self):
        """Запустить планировщик"""
        if self._running:
            logger.warning("Планировщик уже запущен")
            return
        
        self.scheduler.start()
        self._running = True
        logger.info("Планировщик запущен")
    
    def setup_cleanup_job(self, days: int = 90, check_interval_hours: int = 24):
        """
        Настроить автоматическую очистку старых данных
        
        Args:
            days: Удалять данные старше N дней
            check_interval_hours: Интервал проверки
        """
        if not APSCHEDULER_AVAILABLE or not self.scheduler:
            logger.warning("APScheduler недоступен. Очистка не настроена.")
            return
        
        from apscheduler.triggers.interval import IntervalTrigger
        
        self.scheduler.add_job(
            self._cleanup_old_data,
            trigger=IntervalTrigger(hours=check_interval_hours),
            id='cleanup_old_data',
            name='Очистка старых данных',
            replace_existing=True,
            kwargs={'days': days}
        )
        
        logger.info(f"Задача очистки настроена: данные старше {days} дней, проверка каждые {check_interval_hours}ч")
    
    def _cleanup_old_data(self, days: int = 90):
        """Очистить старые данные"""
        from core.database import SessionLocal
        from core.models import Message, Dialogue, Task, AuditLog
        from sqlalchemy import func
        from datetime import timedelta
        
        db = SessionLocal()
        cutoff = now_utc() - timedelta(days=days)
        
        try:
            stats = {"deleted_messages": 0, "deleted_tasks": 0, "deleted_audit": 0}
            
            # Удалить старые прочитанные сообщения (кроме тех что имеют вложения)
            old_messages = db.query(Message).filter(
                Message.created_at < cutoff,
                Message.direction == "inbound",
                Message.is_read == True,
                Message.attachments == []  # Без вложений
            ).delete(synchronize_session=False)
            stats["deleted_messages"] = old_messages
            
            # Удалить выполненные задачи
            old_tasks = db.query(Task).filter(
                Task.created_at < cutoff,
                Task.is_completed == True
            ).delete(synchronize_session=False)
            stats["deleted_tasks"] = old_tasks
            
            # Удалить старые audit logs
            old_audit = db.query(AuditLog).filter(
                AuditLog.created_at < cutoff
            ).delete(synchronize_session=False)
            stats["deleted_audit"] = old_audit
            
            db.commit()
            
            total = sum(stats.values())
            logger.info(f"Очистка завершена: удалено {total} записей (messages={old_messages}, tasks={old_tasks}, audit={old_audit})")
            
            return stats
        
        except Exception as e:
            logger.error(f"Ошибка очистки: {e}")
            db.rollback()
            return {}
        
        finally:
            db.close()
    
    def shutdown(self):
        """Остановка планировщика"""
        if not APSCHEDULER_AVAILABLE:
            return
        
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Планировщик остановлен")
    
    def setup_email_checker(
        self,
        check_interval_hours: int = 1,
        enabled: bool = True
    ):
        """
        Настройка автоматической проверки почты
        
        Args:
            check_interval_hours: Интервал проверки (часы)
            enabled: Включено ли
        """
        if not APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler недоступен. Проверка почты не настроена.")
            return
        
        if not enabled:
            self.remove_job("check_emails")
            logger.info("Проверка почты отключена")
            return
        
        # Функция проверки почты
        def check_emails_job():
            try:
                from services.inbox_service import InboxService
                from services.email_service import EmailService
                
                db = SessionLocal()
                try:
                    inbox_service = InboxService()
                    stats = inbox_service.check_new_emails(db)
                    logger.info(
                        f"Проверка почты: найдено {stats.get('new', 0)} новых писем"
                    )
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Ошибка проверки почты: {e}")
        
        # Запланировать задание
        self.scheduler.add_job(
            check_emails_job,
            trigger=IntervalTrigger(hours=check_interval_hours),
            id="check_emails",
            name="Проверка новых писем",
            replace_existing=True
        )
        
        self._jobs["check_emails"] = {
            "type": "email_check",
            "interval_hours": check_interval_hours
        }
        
        logger.info(
            f"Запущена проверка почты каждые {check_interval_hours} ч"
        )
    
    def setup_reminder_sender(
        self,
        check_interval_minutes: int = 30,
        enabled: bool = True
    ):
        """
        Настройка автоматической отправки напоминаний
        
        Args:
            check_interval_minutes: Интервал проверки (минуты)
            enabled: Включено ли
        """
        if not enabled:
            self.remove_job("send_reminders")
            logger.info("Отправка напоминаний отключена")
            return
        
        # Функция отправки напоминаний
        def send_reminders_job():
            try:
                from services.reminder_service import ReminderService
                
                db = SessionLocal()
                try:
                    reminder_service = ReminderService()
                    stats = reminder_service.send_due_reminders(db)
                    logger.info(
                        f"Отправка напоминаний: {stats['sent']}/{stats['total']}"
                    )
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Ошибка отправки напоминаний: {e}")
        
        # Запланировать задание
        self.scheduler.add_job(
            send_reminders_job,
            trigger=IntervalTrigger(minutes=check_interval_minutes),
            id="send_reminders",
            name="Отправка напоминаний",
            replace_existing=True
        )
        
        self._jobs["send_reminders"] = {
            "type": "reminder_send",
            "interval_minutes": check_interval_minutes
        }
        
        logger.info(
            f"Запущена отправка напоминаний каждые {check_interval_minutes} мин"
        )
    
    def setup_daily_cleanup(
        self,
        hour: int = 2,
        minute: int = 0,
        enabled: bool = True
    ):
        """
        Настройка ежедневной очистки старых данных
        
        Args:
            hour: Час выполнения (0-23)
            minute: Минута выполнения (0-59)
            enabled: Включено ли
        """
        if not enabled:
            self.remove_job("daily_cleanup")
            logger.info("Ежедневная очистка отключена")
            return
        
        # Функция очистки
        def cleanup_job():
            try:
                from services.inbox_service import InboxService
                
                db = SessionLocal()
                try:
                    inbox_service = InboxService()
                    # Очистить прочитанные задачи старше 30 дней
                    cleaned = inbox_service.cleanup_old_tasks(db, days=30)
                    logger.info(f"Ежедневная очистка: удалено {cleaned} записей")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Ошибка ежедневной очистки: {e}")
        
        # Запланировать задание
        self.scheduler.add_job(
            cleanup_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="daily_cleanup",
            name="Ежедневная очистка",
            replace_existing=True
        )
        
        self._jobs["daily_cleanup"] = {
            "type": "cleanup",
            "hour": hour,
            "minute": minute
        }
        
        logger.info(f"Запущена ежедневная очистка в {hour:02d}:{minute:02d}")
    
    def setup_llm_agent_processor(
        self,
        check_interval_minutes: int = 15,
        enabled: bool = True
    ):
        """
        Настройка batch-обработки писем через LLM-агент
        
        Args:
            check_interval_minutes: Интервал обработки (минуты)
            enabled: Включено ли
        """
        if not APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler недоступен. LLM Agent batch не настроен.")
            return
        
        if not enabled:
            self.remove_job("llm_agent_batch")
            logger.info("LLM Agent batch обработка отключена")
            return
        
        def llm_agent_batch_job():
            try:
                from services.llm_agent_service import LLMAgentService
                from core.database import SessionLocal
                
                db = SessionLocal()
                try:
                    agent = LLMAgentService()
                    stats = agent.process_unanswered_dialogues(db)
                    logger.info(
                        f"LLM Agent batch: обработано {stats.get('processed', 0)}, "
                        f"черновиков {stats.get('drafts', 0)}, "
                        f"отправлено {stats.get('sent', 0)}, "
                        f"ошибок {stats.get('errors', 0)}"
                    )
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Ошибка LLM Agent batch: {e}")
        
        self.scheduler.add_job(
            llm_agent_batch_job,
            trigger=IntervalTrigger(minutes=check_interval_minutes),
            id="llm_agent_batch",
            name="LLM Agent batch обработка",
            replace_existing=True
        )
        
        self._jobs["llm_agent_batch"] = {
            "type": "llm_agent_batch",
            "interval_minutes": check_interval_minutes
        }
        
        logger.info(
            f"Запущена LLM Agent batch обработка каждые {check_interval_minutes} мин"
        )
    
    def add_custom_job(
        self,
        job_id: str,
        name: str,
        func: Callable,
        trigger_type: str = "interval",
        **trigger_kwargs
    ):
        """
        Добавить пользовательское задание
        
        Args:
            job_id: Уникальный ID задания
            name: Название задания
            func: Функция для выполнения
            trigger_type: Тип триггера (interval, cron, date)
            **trigger_kwargs: Параметры триггера
        """
        try:
            if trigger_type == "interval":
                trigger = IntervalTrigger(**trigger_kwargs)
            elif trigger_type == "cron":
                trigger = CronTrigger(**trigger_kwargs)
            elif trigger_type == "date":
                from apscheduler.triggers.date import DateTrigger
                trigger = DateTrigger(run_date=trigger_kwargs.get('run_date'))
            else:
                raise ValueError(f"Неизвестный тип триггера: {trigger_type}")
            
            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                name=name,
                replace_existing=True
            )
            
            self._jobs[job_id] = {
                "type": "custom",
                "name": name
            }
            
            logger.info(f"Добавлено задание: {name}")
        
        except Exception as e:
            logger.error(f"Ошибка добавления задания {job_id}: {e}")
            raise
    
    def remove_job(self, job_id: str):
        """
        Удалить задание
        
        Args:
            job_id: ID задания
        """
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self._jobs:
                del self._jobs[job_id]
            logger.info(f"Задание удалено: {job_id}")
        except Exception as e:
            logger.warning(f"Задание {job_id} не найдено: {e}")
    
    def pause_job(self, job_id: str):
        """Пауза задания"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Задание приостановлено: {job_id}")
        except Exception as e:
            logger.error(f"Ошибка паузы {job_id}: {e}")
    
    def resume_job(self, job_id: str):
        """Продолжить задание"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Задание продолжено: {job_id}")
        except Exception as e:
            logger.error(f"Ошибка продолжения {job_id}: {e}")
    
    def get_jobs_status(self) -> Dict:
        """Получить статус всех заданий"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "running": self.scheduler.running,
            "jobs": jobs,
            "registered": list(self._jobs.keys())
        }
    
    def _job_executed_listener(self, event):
        """Обработчик успешного выполнения задания"""
        job = self.scheduler.get_job(event.job_id)
        if job:
            logger.info(f"Задание выполнено: {job.name}")
    
    def _job_error_listener(self, event):
        """Обработчик ошибки задания"""
        job = self.scheduler.get_job(event.job_id)
        if job:
            logger.error(f"Ошибка задания {job.name}: {event.exception}")
