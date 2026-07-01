# Smart-Общага 502 — Задачи

## Инфраструктура
- [x] config.py — централизованные настройки
- [x] requirements.txt — обновить зависимости
- [x] docker-compose.yml — PostgreSQL + bot + prometheus + grafana
- [x] .env.example — шаблон конфигурации

## База данных (PostgreSQL)
- [x] database/connection.py — asyncpg pool
- [x] database/init_db.py — CREATE TABLE всех таблиц
- [x] database/models/queues.py — перенос очередей
- [x] database/models/users.py — пользователи + MAC-адреса
- [x] database/models/finance.py — транзакции / балансы
- [x] database/models/discipline.py — варны / ограничения

## Модули
- [x] modules/presence/worker.py — SSH-воркер опроса роутера
- [x] modules/vpn/controller.py — управление WireGuard (stub)
- [x] modules/finance/calculator.py — расчёт долгов
- [x] modules/finance/scheduler.py — еженедельная рассылка
- [x] modules/discipline/enforcer.py — логика варнов / шейпинга

## Бот — хэндлеры
- [x] bot/middlewares/admin_check.py
- [x] bot/handlers/common.py — /start /help /status /register
- [x] bot/handlers/queues.py — перенос из bot.py
- [x] bot/handlers/finance.py — /buy /balance
- [x] bot/handlers/vpn.py — /vpn_on /vpn_off
- [x] bot/handlers/discipline.py — /warn /unwarn

## Веб
- [x] web_app.py — обновить + новые API
- [x] templates/dashboard.html — полный редизайн

## Точка входа
- [x] main.py — переписать (pool + scheduler + handlers)
