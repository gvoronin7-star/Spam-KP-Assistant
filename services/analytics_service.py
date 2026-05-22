"""
Сервис аналитики и отчётов
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger


class AnalyticsService:
    """
    Сервис для сбора метрик и генерации отчётов
    
    Функции:
    - Статистика по диалогам
    - Статистика по отправителям
    - Статистика по статусам
    - Анализ эффективности автоответов
    - Тренды во времени
    """
    
    def __init__(self):
        self.dialogues = []
        logger.info("AnalyticsService инициализирован")
    
    def get_overall_stats(self, db_session) -> Dict:
        """
        Получить общую статистику
        
        Args:
            db_session: Сессия БД
            
        Returns:
            Словарь с общей статистикой
        """
        from core.models import Dialogue, Message
        
        stats = {
            "total_dialogues": 0,
            "total_messages": 0,
            "total_contacts": 0,
            "kp_received": 0,
            "auto_replies_sent": 0,
            "spam_filtered": 0,
            "dialogues_by_status": {},
            "messages_by_type": {},
            "period_start": None,
            "period_end": None
        }
        
        try:
            # Диалоги
            dialogues = db_session.query(Dialogue).all()
            stats["total_dialogues"] = len(dialogues)
            
            if dialogues:
                stats["period_start"] = min(d.created_at for d in dialogues if d.created_at)
                stats["period_end"] = max(d.created_at for d in dialogues if d.created_at)
            
            # Статусы диалогов
            for dialogue in dialogues:
                status = dialogue.status
                stats["dialogues_by_status"][status] = stats["dialogues_by_status"].get(status, 0) + 1
                
                if status == "kp_received":
                    stats["kp_received"] += 1
                elif status == "spam":
                    stats["spam_filtered"] += 1
                elif status == "auto_replied":
                    stats["auto_replies_sent"] += 1
            
            # Сообщения
            messages = db_session.query(Message).all()
            stats["total_messages"] = len(messages)
            
            # Типы сообщений
            for message in messages:
                msg_type = message.message_type
                stats["messages_by_type"][msg_type] = stats["messages_by_type"].get(msg_type, 0) + 1
            
            # Уникальные контакты
            contacts = set(d.sender_email for d in dialogues if d.sender_email)
            stats["total_contacts"] = len(contacts)
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
        
        return stats
    
    def get_dialogue_timeline(self, db_session, days: int = 30) -> List[Dict]:
        """
        Получить временную шкалу диалогов
        
        Args:
            db_session: Сессия БД
            days: Количество дней для анализа
            
        Returns:
            Список диалогов по дням
        """
        from core.models import Dialogue
        
        timeline = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            dialogues = db_session.query(Dialogue).filter(
                Dialogue.created_at >= cutoff_date
            ).order_by(Dialogue.created_at).all()
            
            # Группировка по дням
            daily_stats = {}
            
            for dialogue in dialogues:
                day = dialogue.created_at.date() if dialogue.created_at else None
                if day:
                    if day not in daily_stats:
                        daily_stats[day] = {
                            "date": day.isoformat(),
                            "total": 0,
                            "kp_received": 0,
                            "spam": 0,
                            "auto_replied": 0
                        }
                    
                    daily_stats[day]["total"] += 1
                    
                    if dialogue.status == "kp_received":
                        daily_stats[day]["kp_received"] += 1
                    elif dialogue.status == "spam":
                        daily_stats[day]["spam"] += 1
                    elif dialogue.status == "auto_replied":
                        daily_stats[day]["auto_replied"] += 1
            
            timeline = list(daily_stats.values())
            
        except Exception as e:
            logger.error(f"Ошибка получения временной шкалы: {e}")
        
        return timeline
    
    def get_top_senders(self, db_session, limit: int = 10) -> List[Dict]:
        """
        Получить топ отправителей
        
        Args:
            db_session: Сессия БД
            limit: Количество результатов
            
        Returns:
            Список отправителей с статистикой
        """
        from core.models import Dialogue
        
        senders = {}
        
        try:
            dialogues = db_session.query(Dialogue).all()
            
            for dialogue in dialogues:
                email = dialogue.sender_email
                if not email:
                    continue
                
                if email not in senders:
                    senders[email] = {
                        "email": email,
                        "dialogue_count": 0,
                        "kp_count": 0,
                        "last_contact": None
                    }
                
                senders[email]["dialogue_count"] += 1
                
                if dialogue.status == "kp_received":
                    senders[email]["kp_count"] += 1
                
                if dialogue.created_at:
                    if (senders[email]["last_contact"] is None or 
                        dialogue.created_at > senders[email]["last_contact"]):
                        senders[email]["last_contact"] = dialogue.created_at
            
            # Сортировка по количеству диалогов
            sorted_senders = sorted(
                senders.values(),
                key=lambda x: x["dialogue_count"],
                reverse=True
            )
            
            return sorted_senders[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка получения топ отправителей: {e}")
            return []
    
    def get_kp_statistics(self, db_session) -> Dict:
        """
        Получить статистику по КП
        
        Args:
            db_session: Сессия БД
            
        Returns:
            Статистика по КП
        """
        from core.models import Dialogue
        
        stats = {
            "total_kp": 0,
            "avg_prices": [],
            "companies": [],
            "price_range": {"min": None, "max": None, "avg": None}
        }
        
        try:
            dialogues = db_session.query(Dialogue).filter_by(status="kp_received").all()
            stats["total_kp"] = len(dialogues)
            
            prices = []
            companies = []
            
            for dialogue in dialogues:
                if dialogue.kp_data:
                    try:
                        kp_data = dialogue.kp_data if isinstance(dialogue.kp_data, dict) else eval(dialogue.kp_data)
                        
                        # Название компании
                        company = dialogue.subject[:50] if dialogue.subject else "Не указано"
                        companies.append(company)
                        
                        # Цены
                        if "prices" in kp_data:
                            for price_item in kp_data["prices"]:
                                try:
                                    price = float(str(price_item.get("price", 0)).replace(" ", "").replace(",", "."))
                                    prices.append(price)
                                except (ValueError, TypeError):
                                    continue
                    except Exception as e:
                        logger.error(f"Ошибка обработки КП {dialogue.id}: {e}")
            
            # Статистика цен
            if prices:
                stats["avg_prices"] = prices
                stats["price_range"] = {
                    "min": min(prices),
                    "max": max(prices),
                    "avg": sum(prices) / len(prices)
                }
            
            stats["companies"] = list(set(companies))
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики КП: {e}")
        
        return stats
    
    def get_efficiency_metrics(self, db_session) -> Dict:
        """
        Получить метрики эффективности
        
        Args:
            db_session: Сессия БД
            
        Returns:
            Метрики эффективности
        """
        from core.models import Dialogue
        
        metrics = {
            "total_incoming": 0,
            "auto_reply_rate": 0.0,
            "kp_rate": 0.0,
            "spam_rate": 0.0,
            "avg_response_time": None
        }
        
        try:
            dialogues = db_session.query(Dialogue).all()
            total = len(dialogues)
            
            if total == 0:
                return metrics
            
            metrics["total_incoming"] = total
            
            auto_replied = sum(1 for d in dialogues if d.status == "auto_replied")
            kp_received = sum(1 for d in dialogues if d.status == "kp_received")
            spam = sum(1 for d in dialogues if d.status == "spam")
            
            metrics["auto_reply_rate"] = round(auto_replied / total * 100, 2)
            metrics["kp_rate"] = round(kp_received / total * 100, 2)
            metrics["spam_rate"] = round(spam / total * 100, 2)
            
        except Exception as e:
            logger.error(f"Ошибка получения метрик эффективности: {e}")
        
        return metrics
    
    def get_monthly_report(self, db_session, year: int = None, month: int = None) -> Dict:
        """
        Получить месячный отчёт
        
        Args:
            db_session: Сессия БД
            year: Год (текущий по умолчанию)
            month: Месяц (текущий по умолчанию)
            
        Returns:
            Месячный отчёт
        """
        from core.models import Dialogue
        
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        report = {
            "year": year,
            "month": month,
            "total_dialogues": 0,
            "kp_received": 0,
            "auto_replies": 0,
            "spam_filtered": 0,
            "unique_contacts": set()
        }
        
        try:
            dialogues = db_session.query(Dialogue).all()
            
            for dialogue in dialogues:
                if dialogue.created_at:
                    if dialogue.created_at.year == year and dialogue.created_at.month == month:
                        report["total_dialogues"] += 1
                        
                        if dialogue.status == "kp_received":
                            report["kp_received"] += 1
                        elif dialogue.status == "auto_replied":
                            report["auto_replies"] += 1
                        elif dialogue.status == "spam":
                            report["spam_filtered"] += 1
                        
                        if dialogue.sender_email:
                            report["unique_contacts"].add(dialogue.sender_email)
            
            report["unique_contacts"] = len(report["unique_contacts"])
            
        except Exception as e:
            logger.error(f"Ошибка получения месячного отчёта: {e}")
        
        return report
    
    def generate_dashboard_data(self, db_session) -> Dict:
        """
        Генерация данных для дашборда
        
        Args:
            db_session: Сессия БД
            
        Returns:
            Данные для дашборда
        """
        dashboard = {
            "overview": self.get_overall_stats(db_session),
            "efficiency": self.get_efficiency_metrics(db_session),
            "kp_stats": self.get_kp_statistics(db_session),
            "top_senders": self.get_top_senders(db_session, limit=5),
            "timeline": self.get_dialogue_timeline(db_session, days=30)
        }
        
        return dashboard
    
    def export_report_to_csv(self, db_session, filepath: str, report_type: str = "overview") -> bool:
        """
        Экспорт отчёта в CSV
        
        Args:
            db_session: Сессия БД
            filepath: Путь к файлу
            report_type: Тип отчёта (overview, kp, senders)
            
        Returns:
            True при успехе
        """
        try:
            import csv
            
            if report_type == "overview":
                data = self.get_overall_stats(db_session)
                rows = [
                    ["Метрика", "Значение"],
                    ["Всего диалогов", data["total_dialogues"]],
                    ["Всего сообщений", data["total_messages"]],
                    ["Уникальных контактов", data["total_contacts"]],
                    ["КП получено", data["kp_received"]],
                    ["Автоответов", data["auto_replies_sent"]],
                    ["Спам отфильтровано", data["spam_filtered"]]
                ]
            elif report_type == "kp":
                data = self.get_kp_statistics(db_session)
                rows = [
                    ["Метрика", "Значение"],
                    ["Всего КП", data["total_kp"]],
                    ["Мин цена", data["price_range"]["min"]],
                    ["Макс цена", data["price_range"]["max"]],
                    ["Средняя цена", data["price_range"]["avg"]]
                ]
            elif report_type == "senders":
                senders = self.get_top_senders(db_session, limit=20)
                rows = [["Email", "Диалогов", "КП"]]
                for sender in senders:
                    rows.append([
                        sender["email"],
                        sender["dialogue_count"],
                        sender["kp_count"]
                    ])
            else:
                logger.error(f"Неизвестный тип отчёта: {report_type}")
                return False
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            
            logger.info(f"Экспорт отчёта в CSV: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в CSV: {e}")
            return False
