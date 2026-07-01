from aiogram import Router, types
from aiogram.filters import Command

from config import ADMIN_IDS, WARN_LIMIT, RESTRICTION_HOURS
from database.models import users as user_db
from database.models.discipline import get_active_restriction
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
        "/status — кто дома и статус VPN\n"
        "/register — зарегистрироваться\n"
        "/addmac — добавить устройство (MAC-адрес)"
        f"{admin_section}"
    )
    await message.answer(text)


@router.message(Command("status"))
async def cmd_status(message: types.Message):
    home_users = await user_db.get_home_users()
    vpn_on = get_vpn_status()

    vpn_text = "🟢 VPN включён" if vpn_on else "🔴 Обычный режим"

    if home_users:
        names = "\n".join(f"  🏠 {u['full_name']}" for u in home_users)
        presence_text = f"<b>Дома ({len(home_users)}):</b>\n{names}"
    else:
        presence_text = "<b>Никого нет дома</b> 🌙"

    await message.answer(
        f"📡 <b>Статус комнаты 502</b>\n\n"
        f"🌐 Сеть: {vpn_text}\n\n"
        f"{presence_text}",
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
            "✅ Вы зарегистрированы в системе!\n"
            "Теперь добавьте ваши устройства командой:\n"
            "<code>/addmac AA:BB:CC:DD:EE:FF</code>",
            parse_mode="HTML",
        )
    else:
        await message.answer("ℹ️ Вы уже зарегистрированы. Данные обновлены.")


@router.message(Command("addmac"))
async def cmd_addmac(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Укажите MAC-адрес устройства:\n<code>/addmac AA:BB:CC:DD:EE:FF</code>",
            parse_mode="HTML",
        )
        return

    mac = args[1].strip()
    # Basic MAC validation
    import re
    if not re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", mac):
        await message.answer("❌ Неверный формат MAC-адреса. Пример: <code>AA:BB:CC:DD:EE:FF</code>", parse_mode="HTML")
        return

    user = await user_db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь: /register")
        return

    added = await user_db.add_mac_address(message.from_user.id, mac)
    if added:
        await message.answer(f"✅ Устройство <code>{mac.upper()}</code> добавлено!", parse_mode="HTML")
    else:
        await message.answer("ℹ️ Этот MAC-адрес уже зарегистрирован.")
