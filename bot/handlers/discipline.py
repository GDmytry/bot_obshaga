from aiogram import Router, types
from aiogram.filters import Command

from config import ADMIN_IDS
from database.models import users as user_db
from database.models.discipline import get_warn_count, get_active_restriction
from modules.discipline.enforcer import handle_warn, handle_unwarn
from config import WARN_LIMIT, RESTRICTION_HOURS

router = Router()


def _require_admin(message: types.Message) -> bool:
    return message.from_user.id in ADMIN_IDS


@router.message(Command("warn"))
async def cmd_warn(message: types.Message):
    """
    /warn @username причина — выдать предупреждение (только для администраторов).
    """
    if not _require_admin(message):
        await message.answer("❌ Эта команда только для администраторов.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "Использование: <code>/warn @username причина</code>",
            parse_mode="HTML",
        )
        return

    mention = args[1].lstrip("@")
    reason = args[2].strip()

    target = await user_db.get_user_by_username(mention)
    if not target:
        await message.answer(
            f"❌ Пользователь @{mention} не найден.\n"
            "Попросите его выполнить /register в боте.",
        )
        return

    result = await handle_warn(
        user_id=target["telegram_id"],
        reason=reason,
        issued_by=message.from_user.id,
    )
    warn_count = result["warn_count"]
    restricted = result["restricted"]

    warn_bar = "⚠️" * warn_count + "⬜" * max(0, WARN_LIMIT - warn_count)

    text = (
        f"⚠️ <b>Предупреждение выдано</b>\n\n"
        f"👤 Пользователь: <b>{target['full_name']}</b>\n"
        f"📝 Причина: {reason}\n"
        f"🔢 Предупреждений: {warn_count}/{WARN_LIMIT} {warn_bar}"
    )

    if restricted:
        text += (
            f"\n\n🚨 <b>Лимит достигнут!</b> Интернет ограничен на {RESTRICTION_HOURS} ч."
        )

    await message.answer(text, parse_mode="HTML")


@router.message(Command("unwarn"))
async def cmd_unwarn(message: types.Message):
    """
    /unwarn @username — снять последнее предупреждение и ограничения (только для администраторов).
    """
    if not _require_admin(message):
        await message.answer("❌ Эта команда только для администраторов.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование: <code>/unwarn @username</code>",
            parse_mode="HTML",
        )
        return

    mention = args[1].lstrip("@").strip()
    target = await user_db.get_user_by_username(mention)
    if not target:
        await message.answer(f"❌ Пользователь @{mention} не найден.")
        return

    result = await handle_unwarn(
        user_id=target["telegram_id"],
        issued_by=message.from_user.id,
    )

    if not result["removed"]:
        await message.answer(
            f"ℹ️ У <b>{target['full_name']}</b> нет активных предупреждений.",
            parse_mode="HTML",
        )
        return

    extra = ""
    if result["restriction_lifted"]:
        extra = "\n✅ Ограничения интернета сняты."

    remaining = await get_warn_count(target["telegram_id"])
    await message.answer(
        f"✅ Предупреждение снято с <b>{target['full_name']}</b>.\n"
        f"Осталось предупреждений: {remaining}/{WARN_LIMIT}{extra}",
        parse_mode="HTML",
    )


@router.message(Command("warns"))
async def cmd_warns(message: types.Message):
    """Показывает текущие предупреждения пользователя."""
    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        # Admin looking up someone else
        if not _require_admin(message):
            await message.answer("❌ Только администраторы могут смотреть чужие варны.")
            return
        mention = args[1].lstrip("@").strip()
        target = await user_db.get_user_by_username(mention)
        if not target:
            await message.answer(f"❌ Пользователь @{mention} не найден.")
            return
    else:
        target = await user_db.get_user(message.from_user.id)
        if not target:
            await message.answer("❌ Вы не зарегистрированы. Выполните /register.")
            return

    from database.models.discipline import get_active_warnings
    warns = await get_active_warnings(target["telegram_id"])
    restriction = await get_active_restriction(target["telegram_id"])

    if not warns:
        await message.answer(f"✅ У <b>{target['full_name']}</b> нет предупреждений.", parse_mode="HTML")
        return

    lines = [f"{i+1}. {w['reason']} (<i>{w['created_at'].strftime('%d.%m %H:%M')}</i>)" for i, w in enumerate(warns)]
    text = (
        f"⚠️ <b>Предупреждения: {target['full_name']}</b>\n\n"
        + "\n".join(lines)
    )
    if restriction:
        expires = restriction["expires_at"].strftime("%d.%m %H:%M")
        text += f"\n\n🚫 <b>Интернет ограничен</b> до {expires}"

    await message.answer(text, parse_mode="HTML")
