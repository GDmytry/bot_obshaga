from decimal import Decimal, InvalidOperation

from aiogram import Router, types
from aiogram.filters import Command

from database.models import finance as fin_db
from database.models import users as user_db

router = Router()


@router.message(Command("buy"))
async def cmd_buy(message: types.Message):
    """
    /buy <сумма> <описание>
    Записывает расход и делит его между всеми активными участниками.
    """
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "Использование: <code>/buy 600 Пельмени</code>\n"
            "Сумма будет разделена между всеми жильцами.",
            parse_mode="HTML",
        )
        return

    try:
        amount = Decimal(args[1].replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Неверная сумма. Пример: <code>/buy 600.50 Пельмени</code>", parse_mode="HTML")
        return

    description = args[2].strip()
    payer_id = message.from_user.id

    # Auto-register payer if not in DB
    await user_db.register_user(
        telegram_id=payer_id,
        username=message.from_user.username,
        full_name=message.from_user.full_name or "Без имени",
    )

    # Get all active users to split with
    all_users = await user_db.get_all_active_users()
    if not all_users:
        await message.answer("❌ Нет зарегистрированных жильцов. Попросите всех выполнить /register.")
        return

    split_with = [u["telegram_id"] for u in all_users]
    # Make sure payer is in the split list
    if payer_id not in split_with:
        split_with.append(payer_id)

    expense_id = await fin_db.add_expense(payer_id, amount, description, split_with)
    share = round(amount / len(split_with), 2)

    payer_name = message.from_user.full_name or "Кто-то"
    others_count = len(split_with) - 1

    await message.answer(
        f"✅ Расход добавлен!\n\n"
        f"💳 <b>{payer_name}</b> заплатил(а) <b>{amount:.2f} ₽</b> за <i>{description}</i>\n"
        f"👥 Делится между {len(split_with)} чел. → <b>{share:.2f} ₽</b> с каждого\n"
        f"💸 {others_count} чел. должны вернуть по {share:.2f} ₽",
        parse_mode="HTML",
    )


@router.message(Command("balance"))
async def cmd_balance(message: types.Message):
    """Показывает матрицу долгов между всеми жильцами."""
    balances = await fin_db.compute_balances()
    all_users = await user_db.get_all_active_users()

    if not balances:
        await message.answer("💚 <b>Баланс чист!</b>\nВсе долги погашены.", parse_mode="HTML")
        return

    name_map: dict[int, str] = {u["telegram_id"]: u["full_name"] for u in all_users}

    lines = []
    for (debtor, creditor), amount in sorted(balances.items(), key=lambda x: -x[1]):
        debtor_name = name_map.get(debtor, f"ID:{debtor}")
        creditor_name = name_map.get(creditor, f"ID:{creditor}")
        lines.append(f"  💸 <b>{debtor_name}</b> → <b>{creditor_name}</b>: {amount:.2f} ₽")

    text = "📊 <b>Баланс «Умного Общака»</b>\n\n" + "\n".join(lines)
    await message.answer(text, parse_mode="HTML")
