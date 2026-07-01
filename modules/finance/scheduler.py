"""
Weekly finance report scheduler.
Sends debt summary to all registered users every Monday at 09:00.
"""

import logging
from database.models.finance import compute_balances
from database.models.users import get_all_active_users, get_user

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

        # What I owe to others
        for (debtor, creditor), amt in balances.items():
            if debtor == uid:
                creditor_name = name_map.get(creditor, f"id:{creditor}")
                lines.append(f"  💸 Вы должны <b>{creditor_name}</b>: <b>{amt:.2f} ₽</b>")

        # What others owe me
        for (debtor, creditor), amt in balances.items():
            if creditor == uid:
                debtor_name = name_map.get(debtor, f"id:{debtor}")
                lines.append(f"  💰 <b>{debtor_name}</b> должен вам: <b>{amt:.2f} ₽</b>")

        if not lines:
            msg = "📊 <b>Еженедельный отчёт «Умного Общака»</b>\n\nВсе долги погашены! ✅"
        else:
            msg = "📊 <b>Еженедельный отчёт «Умного Общака»</b>\n\n" + "\n".join(lines)

        try:
            await _bot.send_message(uid, msg, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"[FinanceScheduler] Could not send to {uid}: {e}")
