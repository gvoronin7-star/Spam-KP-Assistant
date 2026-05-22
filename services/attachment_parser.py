"""
Сервис парсинга вложений (PDF, Excel, Word)

Извлекает текст и табличные данные из файлов КП.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger


class AttachmentParser:
    """Парсер вложений для извлечения текста и данных КП"""
    
    # Поддерживаемые расширения
    SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".docx", ".doc", ".txt", ".csv"}
    
    def __init__(self):
        self._parsers = {
            ".pdf": self._parse_pdf,
            ".xlsx": self._parse_excel,
            ".xls": self._parse_excel,
            ".docx": self._parse_docx,
            ".doc": self._parse_docx,
            ".txt": self._parse_text,
            ".csv": self._parse_text,
        }
        logger.info("AttachmentParser инициализирован")
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Распарсить файл и извлечь текст/данные
        
        Args:
            file_path: Путь к файлу
        
        Returns:
            {
                "text": str,           # Полный текст
                "prices": list,        # Извлечённые цены
                "tables": list,        # Таблицы (список DataFrame-like dict)
                "metadata": dict,      # Метаданные файла
                "error": str           # Ошибка (если есть)
            }
        """
        path = Path(file_path)
        
        if not path.exists():
            return {"text": "", "prices": [], "tables": [], "error": f"Файл не найден: {file_path}"}
        
        ext = path.suffix.lower()
        
        if ext not in self.SUPPORTED_EXTENSIONS:
            return {"text": "", "prices": [], "tables": [], "error": f"Неподдерживаемый формат: {ext}"}
        
        parser = self._parsers.get(ext)
        if not parser:
            return {"text": "", "prices": [], "tables": [], "error": f"Нет парсера для: {ext}"}
        
        try:
            result = parser(file_path)
            result["filename"] = path.name
            result["extension"] = ext
            
            # Извлечь цены из текста (fallback если парсер не извлёк)
            if not result.get("prices") and result.get("text"):
                result["prices"] = self._extract_prices_from_text(result["text"])
            
            logger.info(f"Распарсен {path.name}: {len(result.get('text', ''))} символов, {len(result.get('prices', []))} цен")
            return result
        
        except Exception as e:
            logger.error(f"Ошибка парсинга {path.name}: {e}")
            return {"text": "", "prices": [], "tables": [], "error": str(e)}
    
    def _parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """Парсинг PDF через pdfplumber (предпочтительно) или PyPDF2"""
        text = ""
        tables = []
        
        # Пробуем pdfplumber (лучше для таблиц)
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    
                    # Извлечь таблицы
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table:
                            tables.append(table)
            
            return {"text": text, "prices": [], "tables": tables, "parser": "pdfplumber"}
        
        except ImportError:
            logger.debug("pdfplumber не установлен, пробуем PyPDF2")
        
        # Fallback на PyPDF2
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            return {"text": text, "prices": [], "tables": [], "parser": "PyPDF2"}
        
        except ImportError:
            logger.warning("Ни pdfplumber, ни PyPDF2 не установлены. PDF не может быть распарсен.")
            return {"text": "", "prices": [], "tables": [], "error": "PDF библиотеки не установлены"}
    
    def _parse_excel(self, file_path: str) -> Dict[str, Any]:
        """Парсинг Excel через pandas"""
        try:
            import pandas as pd
            
            # Читаем все листы
            xl = pd.ExcelFile(file_path)
            all_text = []
            all_tables = []
            all_prices = []
            
            for sheet_name in xl.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Текстовое представление
                all_text.append(f"=== Лист: {sheet_name} ===")
                all_text.append(df.to_string(index=False))
                
                # Таблица как dict
                all_tables.append({
                    "sheet": sheet_name,
                    "headers": df.columns.tolist(),
                    "rows": df.head(50).fillna("").to_dict(orient="records")
                })
                
                # Попытка найти цены в таблице
                prices = self._extract_prices_from_dataframe(df)
                all_prices.extend(prices)
            
            return {
                "text": "\n".join(all_text),
                "prices": all_prices,
                "tables": all_tables,
                "parser": "pandas"
            }
        
        except ImportError:
            logger.warning("pandas/openpyxl не установлены. Excel не может быть распарсен.")
            return {"text": "", "prices": [], "tables": [], "error": "pandas/openpyxl не установлены"}
    
    def _parse_docx(self, file_path: str) -> Dict[str, Any]:
        """Парсинг Word через python-docx"""
        try:
            import docx
            doc = docx.Document(file_path)
            
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text.strip())
            
            # Таблицы
            tables = []
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                tables.append(table_data)
            
            text = "\n".join(paragraphs)
            
            return {
                "text": text,
                "prices": [],
                "tables": tables,
                "parser": "python-docx"
            }
        
        except ImportError:
            logger.warning("python-docx не установлен. Word файлы не могут быть распарсены.")
            return {"text": "", "prices": [], "tables": [], "error": "python-docx не установлен"}
    
    def _parse_text(self, file_path: str) -> Dict[str, Any]:
        """Парсинг текстовых файлов"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            
            return {"text": text, "prices": [], "tables": [], "parser": "text"}
        except Exception as e:
            return {"text": "", "prices": [], "tables": [], "error": str(e)}
    
    def _extract_prices_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Извлечь цены из текста регулярками
        
        Returns:
            [{"item": str, "price": float, "currency": str, "unit": str}]
        """
        prices = []
        
        # Паттерны цен
        # "5 000 руб/мес", "5000 руб.", "5 000,00 ₽", "5000.00 RUB"
        price_patterns = [
            # Рубли
            r"(\d[\d\s]*[,.]?\d*)\s*(руб|рублей|₽|RUB)\s*(?:/\s*(мес|мес\.|месяц|год|шт|шт\.|ед|ед\.|час))?",
            # Доллары
            r"(\d[\d\s]*[,.]?\d*)\s*(\$|USD|usd)\s*(?:/\s*(мес|мес\.|месяц|год|шт|шт\.|ед|ед\.|час))?",
            # Евро
            r"(\d[\d\s]*[,.]?\d*)\s*(€|EUR|eur)\s*(?:/\s*(мес|мес\.|месяц|год|шт|шт\.|ед|ед\.|час))?",
        ]
        
        for pattern in price_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                price_str = match.group(1).replace(" ", "").replace(",", ".")
                try:
                    price = float(price_str)
                    currency = match.group(2).upper()
                    unit = match.group(3) if match.group(3) else ""
                    
                    # Нормализация валюты
                    currency_map = {"₽": "RUB", "РУБ": "RUB", "РУБЛЕЙ": "RUB", "$": "USD", "€": "EUR"}
                    currency = currency_map.get(currency, currency)
                    
                    # Попытка найти название позиции (предыдущая строка)
                    start = max(0, match.start() - 200)
                    context = text[start:match.start()]
                    lines = [l.strip() for l in context.split("\n") if l.strip()]
                    item = lines[-1] if lines else ""
                    
                    prices.append({
                        "item": item[:100],
                        "price": price,
                        "currency": currency,
                        "unit": unit,
                        "source": "regex"
                    })
                except ValueError:
                    continue
        
        return prices
    
    def _extract_prices_from_dataframe(self, df) -> List[Dict[str, Any]]:
        """Извлечь цены из pandas DataFrame (Excel таблица)"""
        prices = []
        
        try:
            import pandas as pd
            
            # Найти столбцы с ценами
            price_cols = []
            item_col = None
            
            for col in df.columns:
                col_str = str(col).lower()
                if any(word in col_str for word in ["цена", "price", "стоимость", "сумма", "итого"]):
                    price_cols.append(col)
                if any(word in col_str for word in ["наименование", "название", "услуга", "товар", "item", "описание"]):
                    item_col = col
            
            if not price_cols:
                return prices
            
            # Извлечь данные
            for _, row in df.iterrows():
                for price_col in price_cols:
                    price_val = row.get(price_col)
                    if pd.notna(price_val):
                        try:
                            price = float(str(price_val).replace(" ", "").replace(",", ".").replace("₽", "").replace("$", "").replace("€", ""))
                            
                            item = ""
                            if item_col and item_col in row:
                                item = str(row[item_col])
                            
                            prices.append({
                                "item": item[:100],
                                "price": price,
                                "currency": "RUB",  # По умолчанию
                                "unit": "",
                                "source": "excel_table"
                            })
                        except (ValueError, TypeError):
                            continue
        
        except ImportError:
            pass
        
        return prices
    
    def extract_text_for_llm(self, file_path: str, max_chars: int = 8000) -> str:
        """
        Извлечь текст из файла для передачи в LLM
        
        Args:
            file_path: Путь к файлу
            max_chars: Максимальное количество символов
        
        Returns:
            Текст для LLM
        """
        result = self.parse_file(file_path)
        
        if result.get("error"):
            return f"[Ошибка чтения файла: {result['error']}]"
        
        text = result.get("text", "")
        
        # Добавить таблицы как текст
        tables = result.get("tables", [])
        if tables:
            text += "\n\n=== ТАБЛИЦЫ ===\n"
            for i, table in enumerate(tables[:3]):  # Максимум 3 таблицы
                text += f"\n--- Таблица {i+1} ---\n"
                if isinstance(table, dict) and "rows" in table:
                    # Excel-формат
                    for row in table["rows"][:20]:  # Максимум 20 строк
                        text += " | ".join(str(v) for v in row.values()) + "\n"
                elif isinstance(table, list):
                    # PDF/Word формат
                    for row in table[:20]:
                        if isinstance(row, list):
                            text += " | ".join(str(c) for c in row) + "\n"
        
        # Обрезать
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[... текст обрезан ...]"
        
        return text
