"""
Защита важных файлов от случайного удаления
"""
import os
import shutil
from loguru import logger


def check_guide_file():
    """
    Проверка и восстановление руководства пользователя
    
    Логика:
    1. Если файл существует — ничего не делать (возможно редактировался)
    2. Если файл удалён — создать новую версию из шаблона
    3. Всегда поддерживать резервную копию в data/
    
    Returns:
        bool: True если файл существует или восстановлен, False если не удалось
    """
    # Путь к основному файлу
    guide_path = os.path.join(os.path.dirname(__file__), "..", "docs", "USER_GUIDE.md")
    guide_path = os.path.abspath(guide_path)
    
    # Путь к резервной копии
    backup_path = os.path.join(os.path.dirname(__file__), "..", "data", "backup_guide.md")
    backup_path = os.path.abspath(backup_path)
    
    # Путь к шаблону (если нет бэкапа)
    template_path = os.path.join(os.path.dirname(__file__), "..", "docs", "GUIDE_TEMPLATE.md")
    template_path = os.path.abspath(template_path)
    
    logger.info(f"Проверка руководства: {guide_path}")
    
    # 1. Проверяем: существует ли файл?
    if os.path.exists(guide_path):
        logger.info("✅ Руководство найдено")
        
        # Обновляем резервную копию (если отличается)
        try:
            if not os.path.exists(backup_path) or \
               os.path.getmtime(guide_path) > os.path.getmtime(backup_path):
                shutil.copy2(guide_path, backup_path)
                logger.info("   → Резервная копия обновлена")
        except Exception as e:
            logger.warning(f"   ⚠️ Не удалось обновить резервную копию: {e}")
        
        return True
    
    # 2. Файл не найден! Пробуем восстановить
    logger.warning("⚠️ Руководство не найдено! Восстанавливаю...")
    
    # Сначала пробуем из резервной копии
    if os.path.exists(backup_path):
        try:
            shutil.copy2(backup_path, guide_path)
            logger.info("✅ Руководство восстановлено из резервной копии")
            return True
        except Exception as e:
            logger.error(f"   ✗ Не удалось восстановить из бэкапа: {e}")
    
    # Пробуем из шаблона
    if os.path.exists(template_path):
        try:
            shutil.copy2(template_path, guide_path)
            logger.info("✅ Руководство создано из шаблона")
            return True
        except Exception as e:
            logger.error(f"   ✗ Не удалось создать из шаблона: {e}")
    
    # Создаём минимальную версию
    try:
        create_minimal_guide(guide_path)
        logger.info("✅ Создана минимальная версия руководства")
        return True
    except Exception as e:
        logger.error(f"   ✗ Не удалось создать руководство: {e}")
        return False


def create_minimal_guide(guide_path):
    """Создать минимальную версию руководства"""
    content = """# 📘 Руководство по использованию Spam KP Assistant

**Версия:** 1.0  
**Дата:** 2026-05-20

## ⚠️ Файл был удалён и восстановлен

Этот файл был автоматически создан, потому что оригинал был удалён.

## 📋 Быстрый старт

1. **Профили** — описание услуг (интернет, АТС, линии)
2. **Контакты** — импорт поставщиков из CSV/XLSX
3. **Шаблоны** — письма с переменными
4. **SMTP** — настройка отправки

## 📖 Полная документация

Полная версия руководства доступна по ссылке:
- Встроенная справка в приложении (кнопка "📖 Открыть руководство")
- Папка `docs/` проекта

## 💡 Поддержка

При проблемах обратитесь к разработчику или проверьте логи в `data/app.log`

---

*Файл автоматически создан: {date}*
""".format(date="2026-05-20")
    
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_guide_backup():
    """
    Принудительное обновление резервной копии
    
    Используйте после значительных изменений в руководстве.
    """
    guide_path = os.path.join(os.path.dirname(__file__), "..", "docs", "USER_GUIDE.md")
    guide_path = os.path.abspath(guide_path)
    
    backup_path = os.path.join(os.path.dirname(__file__), "..", "data", "backup_guide.md")
    backup_path = os.path.abspath(backup_path)
    
    if os.path.exists(guide_path):
        shutil.copy2(guide_path, backup_path)
        logger.info(f"✅ Резервная копия обновлена: {backup_path}")
        return True
    else:
        logger.warning("⚠️ Руководство не найдено для резервного копирования")
        return False


def get_guide_path():
    """Получить актуальный путь к руководству"""
    guide_path = os.path.join(os.path.dirname(__file__), "..", "docs", "USER_GUIDE.md")
    return os.path.abspath(guide_path)
