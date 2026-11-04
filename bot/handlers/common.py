from aiogram import Router, types
from aiogram.filters import Command

from config import ADMIN_IDS
from database.models import users as user_db
from modules.vpn.controller import get_vpn_status

router = Router()


@router.message(Command("start", "help"))
async def cmd_start(message: types.Message):
    is_admin = message.from_user.id in ADMIN_IDS
    admin_section = (
        "\n\n🔐 Команды администратора:\n"
        "/warn @user причина — выговор\n"
        "/unwarn @user — снять предупреждение\n"
        "/vpn_on / /vpn_off — управление VPN"
    ) if is_admin else ""

    text = (
        "🏠 Smart-Общага 502\n\n"
        "📋 Очереди:\n"
        "/q Уборка — создать или открыть список\n\n"
        "💰 Умный Общак:\n"
        "/buy 600 Пельмени — добавить расход\n"
        "/balance — баланс долгов\n\n"
        "📡 Информация:\n"
        "/status — список жильцов и статус VPN\n"
        "/register — зарегистрироваться в системе"
        f"{admin_section}"
    )
    await message.answer(text)


@router.message(Command("status"))
async def cmd_status(message: types.Message):
    all_users = await user_db.get_all_active_users()
    vpn_on = get_vpn_status()
    vpn_text = "🟢 VPN включён" if vpn_on else "🔴 Обычный режим"

    if all_users:
        names = "\n".join(f"  👤 {u['full_name']}" for u in all_users)
        residents_text = f"<b>Зарегистрированные жильцы ({len(all_users)}):</b>\n{names}"
    else:
        residents_text = "<i>Нет зарегистрированных жильцов. Выполните /register</i>"

    await message.answer(
        f"📡 <b>Статус комнаты 502</b>\n\n"
        f"🌐 Сеть: {vpn_text}\n\n"
        f"{residents_text}",
        parse_mode="HTML",
    )


@router.message(Command("register"))
async def cmd_register(message: types.Message):
    user = message.from_user
    is_new = await user_db.register_user(
        telegram_id=user.id,
        username=user.username,
        full_name=user.full_name or user.first_name or "Без имени",
    )
    if is_new:
        await message.answer(
            "✅ Вы успешно зарегистрированы в системе комнаты 502!\n"
            "Теперь вы можете участвовать в очередях (/q) и общем бюджете (/buy).",
            parse_mode="HTML",
        )
    else:
        await message.answer("ℹ️ Вы уже зарегистрированы. Данные профиля обновлены.")
