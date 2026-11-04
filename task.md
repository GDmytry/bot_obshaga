# Smart-Общага 502 — Задачи

## Инфраструктура
- [x] config.py — централизованные настройки
- [x] requirements.txt — обновить зависимости
- [x] docker-compose.yml — PostgreSQL + bot + prometheus + grafana
- [x] .env.example — шаблон конфигурации

## База данных (PostgreSQL / SQLite)
- [x] database/connection.py — asyncpg pool + dev pool
- [x] database/init_db.py — CREATE TABLE всех таблиц
- [x] database/models/queues.py — очереди и списки
- [x] database/models/users.py — пользователи
- [x] database/models/finance.py — транзакции / балансы
- [x] database/models/discipline.py — варны / ограничения

## Модули
- [x] modules/vpn/controller.py — управление WireGuard/VPN
- [x] modules/finance/calculator.py — расчёт долгов и сплита
- [x] modules/finance/scheduler.py — еженедельная рассылка
- [x] modules/discipline/enforcer.py — логика варнов / ограничений

## Бот — хэндлеры
- [x] bot/middlewares/admin_check.py
- [x] bot/handlers/common.py — /start /help /status /register
- [x] bot/handlers/queues.py — интерактивные очереди /q
- [x] bot/handlers/finance.py — /buy /balance
- [x] bot/handlers/vpn.py — /vpn_on /vpn_off
- [x] bot/handlers/discipline.py — /warn /unwarn /warns

## Веб
- [x] web_app.py — FastAPI эндпоинты + Mini App
- [x] templates/dashboard.html — дашборд комнаты
- [x] templates/index.html — Mini App для очередей

## Точка входа
- [x] main.py — точка входа (pool + scheduler + handlers)
