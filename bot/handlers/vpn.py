from aiogram import Router, types
from aiogram.filters import Command

from config import ADMIN_IDS
from modules.vpn.controller import enable_vpn, disable_vpn, get_vpn_status

router = Router()


def _require_admin(message: types.Message) -> bool:
    return message.from_user.id in ADMIN_IDS


@router.message(Command("vpn_on"))
async def cmd_vpn_on(message: types.Message):
    if not _require_admin(message):
        await message.answer("❌ Управление VPN доступно только администраторам.")
        return

    if get_vpn_status():
        await message.answer("ℹ️ VPN уже включён.")
        return

    await message.answer("⏳ Включаю VPN…")
    success, output = await enable_vpn()

    if success:
        await message.answer(
            "🟢 <b>VPN включён!</b>\nВесь трафик идёт через туннель.\n"
            f"<code>{output[:200]}</code>",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"❌ Не удалось включить VPN:\n<code>{output[:300]}</code>",
            parse_mode="HTML",
        )


@router.message(Command("vpn_off"))
async def cmd_vpn_off(message: types.Message):
    if not _require_admin(message):
        await message.answer("❌ Управление VPN доступно только администраторам.")
        return

    if not get_vpn_status():
        await message.answer("ℹ️ VPN уже выключен.")
        return

    await message.answer("⏳ Выключаю VPN…")
    success, output = await disable_vpn()

    if success:
        await message.answer(
            "🔴 <b>VPN выключен.</b>\nТрафик идёт через обычный WAN.\n"
            f"<code>{output[:200]}</code>",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"❌ Не удалось выключить VPN:\n<code>{output[:300]}</code>",
            parse_mode="HTML",
        )
