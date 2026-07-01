"""
Discipline Enforcer — применяет и снимает ограничения трафика на роутере.

При достижении лимита варнов:
  1. Создаётся запись в БД (таблица restrictions)
  2. Отправляется SSH-команда на роутер для шейпинга/блокировки по MAC
  3. Планировщик снимает ограничение по истечении expires_at

TODO: Замените команды ниже на реальные для вашего роутера.
OpenWrt (tc + iptables):
  Throttle: tc qdisc add dev br-lan root handle 1: htb && ...
  Block:    iptables -I FORWARD -m mac --mac-source <MAC> -j DROP
HiRouter OS: Поищите в SSH команду `wl` или аналоги для блокировки.
"""

import asyncio
import logging

import paramiko

from config import (
    ROUTER_HOST, ROUTER_PORT, ROUTER_USER,
    ROUTER_PASSWORD, ROUTER_SSH_KEY,
    WARN_LIMIT, RESTRICTION_HOURS, ADMIN_IDS,
)
from database.models import discipline as disc_db
from database.models import users as user_db

logger = logging.getLogger(__name__)

_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


def _run_ssh(command: str) -> tuple[int, str]:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw: dict = dict(hostname=ROUTER_HOST, port=ROUTER_PORT, username=ROUTER_USER, timeout=15)
    if ROUTER_SSH_KEY:
        kw["key_filename"] = ROUTER_SSH_KEY
    else:
        kw["password"] = ROUTER_PASSWORD
    client.connect(**kw)
    _, stdout, stderr = client.exec_command(command)
    out = stdout.read().decode(errors="ignore") + stderr.read().decode(errors="ignore")
    code = stdout.channel.recv_exit_status()
    client.close()
    return code, out


async def _apply_restriction_on_router(mac: str, restriction_type: str) -> bool:
    """
    Send traffic shaping / block command to the router via SSH.
    Returns True on success.

    TODO: Replace stub commands with real router commands.
    """
    loop = asyncio.get_event_loop()

    if restriction_type == "block":
        # TODO: Replace with real block command for your router
        # OpenWrt example: iptables -I FORWARD -m mac --mac-source {mac} -j DROP
        cmd = f"echo 'STUB: block MAC {mac}'"
    else:
        # TODO: Replace with real throttle command for your router
        # OpenWrt tc example sets 64kbps limit
        cmd = f"echo 'STUB: throttle MAC {mac} to 64kbps'"

    try:
        code, out = await loop.run_in_executor(None, _run_ssh, cmd)
        logger.info(f"[Enforcer] Router response ({code}): {out.strip()}")
        return True
    except Exception as exc:
        logger.error(f"[Enforcer] Failed to apply restriction: {exc}")
        return False


async def _lift_restriction_on_router(mac: str) -> bool:
    """
    Remove traffic restrictions for a MAC on the router.
    TODO: Replace with real commands.
    """
    loop = asyncio.get_event_loop()
    # TODO: OpenWrt example: iptables -D FORWARD -m mac --mac-source {mac} -j DROP
    cmd = f"echo 'STUB: lift restriction for MAC {mac}'"
    try:
        await loop.run_in_executor(None, _run_ssh, cmd)
        return True
    except Exception as exc:
        logger.error(f"[Enforcer] Failed to lift restriction: {exc}")
        return False


async def handle_warn(user_id: int, reason: str, issued_by: int) -> dict:
    """
    Issue a warning to a user.
    Automatically applies restriction if warn count reaches WARN_LIMIT.
    Returns a result dict with 'warn_count' and 'restricted' (bool).
    """
    warn_count = await disc_db.add_warning(user_id, reason, issued_by)
    restricted = False

    if warn_count >= WARN_LIMIT:
        # Get user MACs for router commands
        user = await user_db.get_user(user_id)
        macs = [m.strip() for m in user["mac_addresses"].split(",") if m.strip()] if user else []

        restriction_id = await disc_db.add_restriction(
            user_id=user_id,
            restriction_type="throttle",
            reason=f"Автоматически: достигнут лимит {WARN_LIMIT} предупреждений",
            issued_by=issued_by,
            hours=RESTRICTION_HOURS,
        )
        restricted = True

        # Apply on router for each registered MAC
        for mac in macs:
            await _apply_restriction_on_router(mac, "throttle")

        # Notify user
        if _bot:
            try:
                await _bot.send_message(
                    user_id,
                    f"🚨 <b>Внимание!</b>\nВы получили <b>{warn_count}</b> предупреждений "
                    f"и ваш интернет ограничен на <b>{RESTRICTION_HOURS} ч.</b>\n"
                    f"Причина ограничения: {reason}",
                    parse_mode="HTML",
                )
            except Exception:
                pass

    return {"warn_count": warn_count, "restricted": restricted}


async def handle_unwarn(user_id: int, issued_by: int) -> dict:
    """
    Remove the latest warning. If a restriction is active, lift it too.
    Returns {'removed': bool, 'restriction_lifted': bool}
    """
    removed = await disc_db.remove_warning(user_id)
    restriction_lifted = False

    if removed:
        restriction = await disc_db.get_active_restriction(user_id)
        if restriction:
            lifted = await disc_db.lift_restriction(user_id)
            if lifted:
                restriction_lifted = True
                user = await user_db.get_user(user_id)
                macs = [m.strip() for m in user["mac_addresses"].split(",") if m.strip()] if user else []
                for mac in macs:
                    await _lift_restriction_on_router(mac)

                if _bot:
                    try:
                        await _bot.send_message(
                            user_id,
                            "✅ Ограничения с вашего интернета сняты.",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass

    return {"removed": removed, "restriction_lifted": restriction_lifted}


async def expire_restrictions_job() -> None:
    """
    Scheduled job — checks for expired restrictions and lifts them.
    """
    expired_user_ids = await disc_db.expire_old_restrictions()
    for uid in expired_user_ids:
        logger.info(f"[Enforcer] Auto-lifting restriction for user {uid}")
        user = await user_db.get_user(uid)
        if user:
            macs = [m.strip() for m in user["mac_addresses"].split(",") if m.strip()]
            for mac in macs:
                await _lift_restriction_on_router(mac)
        if _bot:
            try:
                await _bot.send_message(
                    uid,
                    "✅ Срок ограничения истёк — доступ в интернет восстановлен.",
                )
            except Exception:
                pass
