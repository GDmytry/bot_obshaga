"""
Weekly finance report scheduler.
Sends debt summary to all registered users every Monday at 09:00.
"""

import logging
from config import MAX_DEBT_LIMIT
from database.models.finance import compute_balances
from database.models.users import get_all_active_users

logger = logging.getLogger(__name__)

_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


async def weekly_report_job() -> None:
    """
    Scheduled job — runs every Monday 09:00.
    Sends each user their personal balance summary.
    """
    logger.info("[FinanceScheduler] Sending weekly balance reports…")
    if not _bot:
        return

    balances = await compute_balances()
    all_users = await get_all_active_users()

    # Build name map
    name_map: dict[int, str] = {u["telegram_id"]: u["full_name"] for u in all_users}

    for user in all_users:
        uid = user["telegram_id"]
        lines = []
        user_total_debt = 0.0

        # What I owe to others
        for (debtor, creditor), amt in balances.items():
            if debtor == uid:
                creditor_name = name_map.get(creditor, f"id:{creditor}")
                lines.append(f"  💸 Вы должны <b>{creditor_name}</b>: <b>{amt:.2f} ₽</b>")
                user_total_debt += amt

        # What others owe me
        for (debtor, creditor), amt in balances.items():
            if creditor == uid:
                debtor_name = name_map.get(debtor, f"id:{debtor}")
                lines.append(f"  💰 <b>{debtor_name}</b> должен вам: <b>{amt:.2f} ₽</b>")

        if not lines:
            msg = "📊 <b>Еженедельный отчёт «Умного Общака»</b>\n\nВсе долги погашены! ✅"
        else:
            msg = "📊 <b>Еженедельный отчёт «Умного Общака»</b>\n\n" + "\n".join(lines)
            if user_total_debt >= MAX_DEBT_LIMIT:
                msg += (
                    f"\n\n⚠️ <b>Внимание:</b> ваш долг (<b>{user_total_debt:.2f} ₽</b>) "
                    f"превышает лимит (<b>{MAX_DEBT_LIMIT:.2f} ₽</b>). "
                    "Пожалуйста, закройте задолженность!"
                )

        try:
            await _bot.send_message(uid, msg, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"[FinanceScheduler] Could not send to {uid}: {e}")
