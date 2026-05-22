"""
Тесты для SchedulerService
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys


def _get_scheduler_service():
    """Получить SchedulerService с чистым импортом"""
    # Удаляем кэш модуля, чтобы импортировать заново
    for key in list(sys.modules.keys()):
        if key.startswith('services.scheduler_service'):
            del sys.modules[key]
    
    with patch('apscheduler.schedulers.background.BackgroundScheduler'):
        with patch('apscheduler.jobstores.sqlalchemy.SQLAlchemyJobStore'):
            with patch('apscheduler.triggers.interval.IntervalTrigger'):
                with patch('apscheduler.triggers.cron.CronTrigger'):
                    with patch('apscheduler.events.EVENT_JOB_ERROR', 1):
                        with patch('apscheduler.events.EVENT_JOB_EXECUTED', 2):
                            from services.scheduler_service import SchedulerService
                            return SchedulerService()


class TestSchedulerService:
    """Тесты планировщика"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.scheduler = _get_scheduler_service()
        self.scheduler.scheduler = MagicMock()
        self.scheduler.scheduler.running = False
        self.scheduler._jobs = {}
    
    def test_init(self):
        """Инициализация сервиса"""
        assert self.scheduler is not None
        assert self.scheduler._jobs == {}
    
    def test_start(self):
        """Запуск планировщика"""
        self.scheduler.start()
        self.scheduler.scheduler.start.assert_called_once()
    
    def test_shutdown(self):
        """Остановка планировщика"""
        self.scheduler.scheduler.running = True
        self.scheduler.shutdown()
        self.scheduler.scheduler.shutdown.assert_called_once_with(wait=True)
    
    @patch('services.scheduler_service.IntervalTrigger')
    def test_setup_email_checker(self, mock_interval_trigger):
        """Настройка проверки почты"""
        mock_interval_trigger.return_value = MagicMock()
        
        self.scheduler.setup_email_checker(
            check_interval_hours=2,
            enabled=True
        )
        
        assert "check_emails" in self.scheduler._jobs
        assert self.scheduler._jobs["check_emails"]["interval_hours"] == 2
        
        self.scheduler.scheduler.add_job.assert_called_once()
    
    @patch('services.scheduler_service.IntervalTrigger')
    def test_setup_reminder_sender(self, mock_interval_trigger):
        """Настройка отправки напоминаний"""
        mock_interval_trigger.return_value = MagicMock()
        
        self.scheduler.setup_reminder_sender(
            check_interval_minutes=15,
            enabled=True
        )
        
        assert "send_reminders" in self.scheduler._jobs
        assert self.scheduler._jobs["send_reminders"]["interval_minutes"] == 15
    
    @patch('services.scheduler_service.CronTrigger')
    def test_setup_daily_cleanup(self, mock_cron_trigger):
        """Настройка ежедневной очистки"""
        mock_cron_trigger.return_value = MagicMock()
        
        self.scheduler.setup_daily_cleanup(
            hour=3,
            minute=30,
            enabled=True
        )
        
        assert "daily_cleanup" in self.scheduler._jobs
        assert self.scheduler._jobs["daily_cleanup"]["hour"] == 3
        assert self.scheduler._jobs["daily_cleanup"]["minute"] == 30
    
    def test_remove_job(self):
        """Удаление задания"""
        # Сначала добавить задание
        self.scheduler._jobs["test_job"] = {"type": "test"}
        
        # Удалить
        self.scheduler.remove_job("test_job")
        
        assert "test_job" not in self.scheduler._jobs
    
    def test_get_jobs_status(self):
        """Получение статуса заданий"""
        self.scheduler._jobs["job1"] = {"type": "email_check"}
        self.scheduler._jobs["job2"] = {"type": "reminder_send"}
        
        self.scheduler.scheduler.get_jobs.return_value = []
        
        status = self.scheduler.get_jobs_status()
        
        assert status["running"] == False
        assert len(status["registered"]) == 2
        assert "job1" in status["registered"]
        assert "job2" in status["registered"]
    
    def test_pause_job(self):
        """Пауза задания"""
        self.scheduler.pause_job("test_job")
        self.scheduler.scheduler.pause_job.assert_called_once_with("test_job")
    
    def test_resume_job(self):
        """Продолжение задания"""
        self.scheduler.resume_job("test_job")
        self.scheduler.scheduler.resume_job.assert_called_once_with("test_job")
    
    def test_add_custom_job(self):
        """Добавление пользовательского задания"""
        def dummy_func():
            pass
        
        self.scheduler.add_custom_job(
            job_id="custom_1",
            name="Тестовое задание",
            func=dummy_func,
            trigger_type="interval",
            hours=1
        )
        
        assert "custom_1" in self.scheduler._jobs
        assert self.scheduler._jobs["custom_1"]["name"] == "Тестовое задание"
    
    def test_disable_email_checker(self):
        """Отключение проверки почты"""
        self.scheduler._jobs["check_emails"] = {"type": "email_check"}
        
        self.scheduler.setup_email_checker(enabled=False)
        
        assert "check_emails" not in self.scheduler._jobs


class TestSchedulerIntegration:
    """Интеграционные тесты планировщика"""
    
    def test_scheduler_with_mock_services(self):
        """Планировщик с мок-сервисами"""
        scheduler = _get_scheduler_service()
        scheduler.scheduler = MagicMock()
        scheduler.scheduler.running = False
        
        # Запустить все задачи
        scheduler.start()
        scheduler.setup_email_checker(check_interval_hours=1, enabled=True)
        scheduler.setup_reminder_sender(check_interval_minutes=30, enabled=True)
        scheduler.setup_daily_cleanup(hour=2, minute=0, enabled=True)
        
        # Проверить что все задания добавлены
        assert len(scheduler._jobs) == 3
        
        # Остановить
        scheduler.scheduler.running = True
        scheduler.shutdown()
        scheduler.scheduler.shutdown.assert_called_once()
