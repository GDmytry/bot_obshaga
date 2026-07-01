import asyncio
import logging
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat, MenuButtonWebApp, WebAppInfo
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from database.connection import create_pool, close_pool
from database.init_db import init_db

# Bot handlers
from bot.handlers import common, queues, finance, vpn, discipline
from bot.middlewares.admin_check import AdminMiddleware

# Module workers/schedulers
from modules.presence import worker as presence_worker
from modules.discipline import enforcer
from modules.finance import scheduler as finance_scheduler

# Web app
from web_app import app as web_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def register_commands(bot: Bot) -> None:
    """Set bot command list visible in the Telegram menu."""

    # Commands for all users
    user_commands = [
        BotCommand(command="start",    description="🏟️ Главное меню и справка"),
        BotCommand(command="status",   description="📡 Кто дома и статус VPN"),
        BotCommand(command="register", description="👤 Зарегистрироваться в системе"),
        BotCommand(command="addmac",   description="📱 Добавить MAC-адрес устройства"),
        BotCommand(command="buy",      description="🛒 /buy 600 Пельмени — добавить расход в общак"),
        BotCommand(command="balance",  description="📊 Матрица долгов"),
        BotCommand(command="q",        description="📋 /q Уборка — создать/открыть список"),
        BotCommand(command="warns",    description="⚠️ Мои предупреждения"),
        BotCommand(command="help",     description="ℹ️ Помощь"),
    ]

    # Extra commands for admins
    admin_commands = user_commands + [
        BotCommand(command="vpn_on",   description="🟢 Включить VPN"),
        BotCommand(command="vpn_off",  description="🔴 Выключить VPN"),
        BotCommand(command="warn",     description="⚠️ /warn @user причина — выговор"),
        BotCommand(command="unwarn",   description="✅ /unwarn @user — снять предупреждение"),
    ]

    # Set for all users globally
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    if config.WEBAPP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Дашборд 📱",
                web_app=WebAppInfo(url=config.WEBAPP_URL)
            )
        )

    # Override per admin — show extended list in their private chat
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception as e:
            logger.warning(f"Could not set admin commands for {admin_id}: {e}")

    logger.info("✅ Bot commands registered.")


async def start_bot(bot: Bot, dp: Dispatcher) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await register_commands(bot)
    await dp.start_polling(bot)


async def start_web() -> None:
    server_config = uvicorn.Config(
        web_app, host="0.0.0.0", port=8000, log_level="info"
    )
    server = uvicorn.Server(server_config)
    await server.serve()


async def main() -> None:
    await create_pool()
    await init_db()

    # ── Bot setup ─────────────────────────────────────────────
    if config.PROXY_URL:
        session = AiohttpSession(proxy=config.PROXY_URL)
        bot = Bot(token=config.BOT_TOKEN, session=session)
        logger.info(f"Bot starting with proxy: {config.PROXY_URL}")
    else:
        bot = Bot(token=config.BOT_TOKEN)

    dp = Dispatcher()

    dp.message.middleware(AdminMiddleware())

    dp.include_router(common.router)
    dp.include_router(queues.router)
    dp.include_router(finance.router)
    dp.include_router(vpn.router)
    dp.include_router(discipline.router)

    presence_worker.set_bot(bot)
    enforcer.set_bot(bot)
    finance_scheduler.set_bot(bot)

    # ── Scheduler ─────────────────────────────────────────────
    scheduler = AsyncIOScheduler()

    # Presence check every 2 minutes
    scheduler.add_job(
        presence_worker.presence_check_job,
        trigger="interval",
        minutes=2,
        id="presence_check",
    )

    # Auto-lift expired restrictions every 5 minutes
    scheduler.add_job(
        enforcer.expire_restrictions_job,
        trigger="interval",
        minutes=5,
        id="expire_restrictions",
    )

    # Weekly finance report — every Monday at 09:00
    scheduler.add_job(
        finance_scheduler.weekly_report_job,
        trigger="cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        id="weekly_report",
    )

    scheduler.start()
    logger.info("✅ Scheduler started.")

    # ── Run everything concurrently ────────────────────────────
    try:
        await asyncio.gather(
            start_bot(bot, dp),
            start_web(),
        )
    finally:
        scheduler.shutdown(wait=False)
        await close_pool()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
