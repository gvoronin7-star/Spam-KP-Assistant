# Alembic Migrations

## Инициализация (уже выполнена)

```bash
python -m alembic.config revision --autogenerate -m "Initial migration"
```

## Создание новой миграции

```bash
python -m alembic.config revision --autogenerate -m "Описание изменений"
```

## Применение миграций

```bash
python -m alembic.config upgrade head
```

## Откат на одну миграцию

```bash
python -m alembic.config downgrade -1
```

## Просмотр истории

```bash
python -m alembic.config history
```

## Текущая версия

```bash
python -m alembic.config current
```

## Для production

```bash
# Сначала backup БД
copy data\spam_kp_assistant.db data\spam_kp_assistant.db.backup

# Затем миграция
python -m alembic.config upgrade head
```
