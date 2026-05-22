"""
Сервис сравнения коммерческих предложений (KP)
"""
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger


class KPComparisonService:
    """
    Сервис для сбора и сравнения коммерческих предложений
    
    Функции:
    - Извлечение данных КП из диалогов
    - Нормализация цен и валют
    - Сравнение по ключевым параметрам
    - Генерация отчётов
    """
    
    def __init__(self):
        self.dialogues = []
        self.comparisons = []
        logger.info("KPComparisonService инициализирован")
    
    def extract_kp_data(self, dialogue) -> Optional[Dict]:
        """
        Извлечь данные КП из диалога
        
        Args:
            dialogue: Объект Dialogue из БД
            
        Returns:
            Словарь с данными КП или None
        """
        if not dialogue or not dialogue.kp_data:
            return None
        
        try:
            # Парсинг JSON
            kp_data = dialogue.kp_data if isinstance(dialogue.kp_data, dict) else eval(dialogue.kp_data)
            
            # Извлечение основных полей
            kp_info = {
                "dialogue_id": dialogue.id,
                "dialogue_status": dialogue.status,
                "company_name": self._extract_company_name(dialogue),
                "contact_person": self._extract_contact_person(dialogue),
                "email": dialogue.sender_email,
                "received_at": dialogue.created_at,
                "prices": kp_data.get("prices", []),
                "terms": kp_data.get("terms", []),
                "notes": kp_data.get("notes", ""),
                "attachments": kp_data.get("attachments", []),
                "total_price": self._calculate_total_price(kp_data.get("prices", [])),
                "currency": self._extract_currency(kp_data.get("prices", [])),
                "delivery_time": self._extract_delivery_time(kp_data.get("terms", [])),
                "payment_terms": self._extract_payment_terms(kp_data.get("terms", []))
            }
            
            return kp_info
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных КП из диалога {dialogue.id}: {e}")
            return None
    
    def _extract_company_name(self, dialogue) -> str:
        """Извлечь название компании из диалога"""
        if not dialogue.subject:
            return "Не указано"
        
        # Попытка найти название компании в теме письма
        subject = dialogue.subject.lower()
        
        # Очистка от служебных слов
        for word in ["кп", "коммерческое предложение", "от", "предложение", "цены"]:
            subject = subject.replace(word, "")
        
        company_name = subject.strip().strip("()-\"'")
        
        return company_name if company_name else "Не указано"
    
    def _extract_contact_person(self, dialogue) -> str:
        """Извлечь контактное лицо"""
        # Берём из последних сообщений
        if dialogue.messages:
            last_message = sorted(dialogue.messages, key=lambda m: m.created_at, reverse=True)[0]
            if last_message.from_sender:
                # Извлекаем имя из email (до @)
                email = last_message.sender_email
                name = email.split("@")[0].replace(".", " ").replace("_", " ").title()
                return name
        
        return "Не указано"
    
    def _calculate_total_price(self, prices: List[Dict]) -> float:
        """Рассчитать общую сумму"""
        total = 0.0
        
        for price_item in prices:
            try:
                price_str = price_item.get("price", "0")
                # Убрать пробелы и символ валюты
                price_str = price_str.replace(" ", "").replace("₽", "").replace("RUB", "").strip()
                price = float(price_str)
                total += price
            except (ValueError, AttributeError):
                continue
        
        return total
    
    def _extract_currency(self, prices: List[Dict]) -> str:
        """Определить валюту"""
        if not prices:
            return "RUB"
        
        # Проверить первое предложение
        first = prices[0]
        currency = first.get("currency", "RUB")
        
        if currency:
            return currency.upper()
        
        return "RUB"
    
    def _extract_delivery_time(self, terms: List[Dict]) -> str:
        """Извлечь срок поставки"""
        for term in terms:
            if "поставк" in term.get("name", "").lower() or "срок" in term.get("name", "").lower():
                return term.get("value", "Не указано")
        
        return "Не указано"
    
    def _extract_payment_terms(self, terms: List[Dict]) -> str:
        """Извлечь условия оплаты"""
        for term in terms:
            if "оплат" in term.get("name", "").lower() or "предоплат" in term.get("name", "").lower():
                return term.get("value", "Не указано")
        
        return "Не указано"
    
    def compare_dialogues(self, dialogue_ids: List[int]) -> Dict:
        """
        Сравнить несколько диалогов с КП
        
        Args:
            dialogue_ids: Список ID диалогов
            
        Returns:
            Словарь с результатами сравнения
        """
        from core.database import SessionLocal
        from core.models import Dialogue
        
        kp_list = []
        db = SessionLocal()
        try:
            for dialogue_id in dialogue_ids:
                dialogue = db.query(Dialogue).filter_by(id=dialogue_id).first()
                if dialogue:
                    kp_info = self.extract_kp_data(dialogue)
                    if kp_info:
                        kp_list.append(kp_info)
        finally:
            db.close()
        
        # Сортировка по общей цене
        kp_list.sort(key=lambda x: x["total_price"])
        
        # Определение лучших предложений
        best_price = kp_list[0] if kp_list else None
        best_delivery = self._find_best_delivery(kp_list)
        best_terms = self._find_best_terms(kp_list)
        
        comparison = {
            "kp_list": kp_list,
            "count": len(kp_list),
            "best_price": best_price,
            "best_delivery": best_delivery,
            "best_terms": best_terms,
            "generated_at": datetime.now().isoformat()
        }
        
        self.comparisons.append(comparison)
        
        logger.info(f"Сравнено {len(kp_list)} КП")
        
        return comparison
    
    def _find_best_delivery(self, kp_list: List[Dict]) -> Optional[Dict]:
        """Найти лучшее предложение по срокам"""
        if not kp_list:
            return None
        
        # Простая эвристика: искать минимальное количество дней
        best = None
        min_days = float('inf')
        
        for kp in kp_list:
            delivery = kp.get("delivery_time", "")
            try:
                # Попытка извлечь число дней
                days = int(''.join(filter(str.isdigit, delivery)) or '999')
                if days < min_days:
                    min_days = days
                    best = kp
            except (ValueError, TypeError):
                continue
        
        return best
    
    def _find_best_terms(self, kp_list: List[Dict]) -> Optional[Dict]:
        """Найти лучшее предложение по условиям (предоплата)"""
        if not kp_list:
            return None
        
        # Предпочитаем 0% предоплаты
        best = None
        min_prepayment = 100
        
        for kp in kp_list:
            payment = kp.get("payment_terms", "")
            try:
                percent = int(''.join(filter(str.isdigit, payment)) or '100')
                if percent < min_prepayment:
                    min_prepayment = percent
                    best = kp
            except (ValueError, TypeError):
                continue
        
        return best
    
    def get_comparison_matrix(self, dialogue_ids: List[int]) -> List[Dict]:
        """
        Получить матрицу сравнения для GUI
        
        Args:
            dialogue_ids: Список ID диалогов
            
        Returns:
            Список строк для таблицы сравнения
        """
        comparison = self.compare_dialogues(dialogue_ids)
        
        matrix = []
        
        for kp in comparison["kp_list"]:
            row = {
                "dialogue_id": kp["dialogue_id"],
                "company": kp["company_name"],
                "contact": kp["contact_person"],
                "email": kp["email"],
                "total_price": kp["total_price"],
                "currency": kp["currency"],
                "delivery_time": kp["delivery_time"],
                "payment_terms": kp["payment_terms"],
                "items_count": len(kp["prices"]),
                "notes": kp["notes"][:100] + "..." if len(kp["notes"]) > 100 else kp["notes"]
            }
            matrix.append(row)
        
        return matrix
    
    def export_to_excel(self, dialogue_ids: List[int], filepath: str) -> bool:
        """
        Экспорт сравнения в Excel
        
        Args:
            dialogue_ids: Список ID диалогов
            filepath: Путь к файлу Excel
            
        Returns:
            True при успехе
        """
        try:
            import pandas as pd
            
            matrix = self.get_comparison_matrix(dialogue_ids)
            
            if not matrix:
                logger.warning("Нет данных для экспорта")
                return False
            
            df = pd.DataFrame(matrix)
            
            # Форматирование
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Сравнение КП')
                
                # Настройка ширины колонок
                worksheet = writer.sheets['Сравнение КП']
                worksheet.column_dimensions['A'].width = 10  # ID
                worksheet.column_dimensions['B'].width = 25  # Компания
                worksheet.column_dimensions['C'].width = 20  # Контакт
                worksheet.column_dimensions['D'].width = 30  # Email
                worksheet.column_dimensions['E'].width = 15  # Цена
                worksheet.column_dimensions['F'].width = 10  # Валюта
                worksheet.column_dimensions['G'].width = 20  # Поставка
                worksheet.column_dimensions['H'].width = 25  # Оплата
            
            logger.info(f"Экспорт в Excel: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в Excel: {e}")
            return False
    
    def get_price_comparison(self, dialogue_ids: List[int]) -> Dict:
        """
        Получить сравнение цен по позициям
        
        Args:
            dialogue_ids: Список ID диалогов
            
        Returns:
            Словарь с ценами по позициям
        """
        comparison = self.compare_dialogues(dialogue_ids)
        
        # Собрать все уникальные услуги
        all_services = set()
        for kp in comparison["kp_list"]:
            for price_item in kp.get("prices", []):
                service = price_item.get("service", "")
                if service:
                    all_services.add(service)
        
        # Построить матрицу цен
        price_matrix = {}
        
        for service in all_services:
            price_matrix[service] = {}
            
            for kp in comparison["kp_list"]:
                for price_item in kp.get("prices", []):
                    if price_item.get("service") == service:
                        company = kp["company_name"]
                        price = price_item.get("price", "0")
                        price_matrix[service][company] = price
        
        return {
            "services": list(all_services),
            "price_matrix": price_matrix,
            "companies": [kp["company_name"] for kp in comparison["kp_list"]]
        }
