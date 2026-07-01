"""Queue handlers — migrated from the original bot.py to use asyncpg."""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import WEBAPP_URL, MINI_APP_LINK
from database.models import queues as q_db

router = Router()


def get_queue_keyboard(queue_id: int, chat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Присоединиться ➕", callback_data=f"join_{queue_id}")
    builder.button(text="Покинуть ➖", callback_data=f"leave_{queue_id}")
    builder.button(text="Отметиться ✅", callback_data=f"done_{queue_id}")
    builder.button(text="Сбросить 🔄", callback_data=f"undone_{queue_id}")
    if MINI_APP_LINK:
        builder.button(text="Открыть дашборд 📱", url=f"{MINI_APP_LINK}?startapp={chat_id}")
    elif WEBAPP_URL and chat_id > 0:
        builder.button(
            text="Открыть дашборд 📱",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?chat_id={chat_id}"),
        )
    builder.adjust(2, 1, 1)
    return builder.as_markup()


async def format_queue_text(queue_id: int, queue_name: str) -> str:
    members = await q_db.get_queue_members(queue_id)
    text = f"📋 <b>Список: {queue_name}</b>\n\n"
    if not members:
        text += "Список пуст. Нажмите кнопку ниже, чтобы присоединиться!"
    else:
        for idx, m in enumerate(members):
            if m["is_done"]:
                text += f"{idx + 1}. ✅ <s>{m['user_name']}</s> ({m['done_time']})\n"
            else:
                text += f"{idx + 1}. ⏳ {m['user_name']}\n"
    return text


@router.message(Command("q"))
async def cmd_q(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пожалуйста, укажите название очереди. Например: <code>/q Уборка</code>", parse_mode="HTML")
        return

    queue_name = args[1].strip()
    chat_id = message.chat.id

    queue = await q_db.get_queue(chat_id, queue_name)
    if not queue:
        queue_id = await q_db.create_queue(chat_id, queue_name)
        if not queue_id:
            await message.answer("Произошла ошибка при создании очереди.")
            return
    else:
        queue_id = queue["id"]

    text = await format_queue_text(queue_id, queue_name)
    await message.answer(text, reply_markup=get_queue_keyboard(queue_id, chat_id), parse_mode="HTML")


@router.callback_query(F.data.startswith("join_"))
async def cb_join(callback: types.CallbackQuery):
    queue_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name or callback.from_user.username or "Без имени"

    success = await q_db.join_queue(queue_id, user_id, user_name)
    if success:
        queue = await q_db.get_queue_by_id(queue_id)
        if queue:
            text = await format_queue_text(queue_id, queue["name"])
            await callback.message.edit_text(
                text, reply_markup=get_queue_keyboard(queue_id, queue["chat_id"]), parse_mode="HTML"
            )
        await callback.answer("Вы добавлены в очередь!")
    else:
        await callback.answer("Вы уже в этой очереди!", show_alert=True)


@router.callback_query(F.data.startswith("leave_"))
async def cb_leave(callback: types.CallbackQuery):
    queue_id = int(callback.data.split("_")[1])
    success = await q_db.leave_queue(queue_id, callback.from_user.id)
    if success:
        queue = await q_db.get_queue_by_id(queue_id)
        if queue:
            text = await format_queue_text(queue_id, queue["name"])
            await callback.message.edit_text(
                text, reply_markup=get_queue_keyboard(queue_id, queue["chat_id"]), parse_mode="HTML"
            )
        await callback.answer("Вы покинули очередь!")
    else:
        await callback.answer("Вас нет в этой очереди!", show_alert=True)


@router.callback_query(F.data.startswith("done_"))
async def cb_done(callback: types.CallbackQuery):
    queue_id = int(callback.data.split("_")[1])
    queue = await q_db.get_queue_by_id(queue_id)
    if not queue:
        await callback.answer("Очередь не найдена.")
        return

    success = await q_db.mark_done(queue_id, callback.from_user.id)
    if success:
        actor_name = callback.from_user.full_name or callback.from_user.username or "Кто-то"
        await callback.message.answer(
            f"✅ <b>{actor_name}</b> отметил(а) выполнение задачи «{queue['name']}».",
            parse_mode="HTML",
        )
        text = await format_queue_text(queue_id, queue["name"])
        await callback.message.edit_text(
            text, reply_markup=get_queue_keyboard(queue_id, queue["chat_id"]), parse_mode="HTML"
        )
        await callback.answer("Отмечено!")
    else:
        await callback.answer("Ошибка: вы не в списке или уже отметились.", show_alert=True)


@router.callback_query(F.data.startswith("undone_"))
async def cb_undone(callback: types.CallbackQuery):
    queue_id = int(callback.data.split("_")[1])
    queue = await q_db.get_queue_by_id(queue_id)
    if not queue:
        await callback.answer("Список не найден.")
        return

    success = await q_db.unmark_done(queue_id, callback.from_user.id)
    if success:
        text = await format_queue_text(queue_id, queue["name"])
        await callback.message.edit_text(
            text, reply_markup=get_queue_keyboard(queue_id, queue["chat_id"]), parse_mode="HTML"
        )
        await callback.answer("Отметка снята!")
    else:
        await callback.answer("Ошибка: вас нет в списке или вы еще не отмечались.", show_alert=True)
