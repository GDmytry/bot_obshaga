"""
Presence Worker — периодически опрашивает роутер Huawei AX2 по SSH,
парсит ARP-таблицу и обновляет статусы пользователей в БД.

Huawei AX2 (WS7200) работает на HiRouter OS.
SSH должен быть включён вручную в веб-интерфейсе роутера
(Дополнительно → Инструменты → Терминал / SSH).

Команды для получения подключённых устройств:
  - `arp -a`                     — стандартная ARP-таблица
  - `cat /proc/net/arp`          — альтернативный источник
  - `iwinfo wlan0 assoclist`     — ассоциации Wi-Fi (если есть OpenWrt-утилиты)
"""

import asyncio
import logging
import re
from datetime import datetime, timezone

import paramiko

from config import (
    ROUTER_HOST, ROUTER_PORT, ROUTER_USER,
    ROUTER_PASSWORD, ROUTER_SSH_KEY, ADMIN_IDS,
)
from database.models import users as user_db
from database.models.discipline import get_active_restriction

logger = logging.getLogger(__name__)

# Will be injected by main.py after bot is created
_router_is_down = False
_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


def _ssh_get_macs() -> list[str]:
    """
    Open an SSH session to the router and parse connected MAC addresses.
    Returns a list of uppercase MAC strings like ['AA:BB:CC:DD:EE:FF', ...].

    TODO: Adjust the command if `arp -a` is not available on your Huawei AX2 firmware.
    Alternative: `cat /proc/net/arp` or check /tmp/dhcp.leases
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict = dict(
        hostname=ROUTER_HOST,
        port=ROUTER_PORT,
        username=ROUTER_USER,
        timeout=10,
    )
    if ROUTER_SSH_KEY:
        connect_kwargs["key_filename"] = ROUTER_SSH_KEY
    else:
        connect_kwargs["password"] = ROUTER_PASSWORD

    client.connect(**connect_kwargs)

    # Primary: standard ARP table
    # TODO: if AX2 doesn't have `arp`, try `cat /proc/net/arp`
    _, stdout, _ = client.exec_command("arp -a 2>/dev/null || cat /proc/net/arp")
    output = stdout.read().decode(errors="ignore")
    client.close()

    # Parse MACs — matches patterns like aa:bb:cc:dd:ee:ff
    macs = re.findall(r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})", output)
    return [m.upper() for m in macs]


async def presence_check_job() -> None:
    """
    Scheduled job: runs every ~2 minutes via APScheduler.
    Fetches active MACs from the router, updates user statuses,
    and notifies admins on connection changes.
    """
    global _router_is_down
    logger.info("[PresenceWorker] Running presence check…")
    try:
        # Run blocking SSH call in a thread pool
        loop = asyncio.get_event_loop()
        active_macs: list[str] = await loop.run_in_executor(None, _ssh_get_macs)
        logger.info(f"[PresenceWorker] Detected MACs: {active_macs}")
        
        if _router_is_down:
            _router_is_down = False
            if _bot and ADMIN_IDS:
                for admin_id in ADMIN_IDS:
                    try:
                        await _bot.send_message(admin_id, "✅ <b>Роутер снова доступен!</b>\nСвязь восстановлена.", parse_mode="HTML")
                    except Exception:
                        pass

    except Exception as exc:
        logger.warning(f"[PresenceWorker] Router unreachable: {exc}")
        if not _router_is_down:
            _router_is_down = True
            if _bot and ADMIN_IDS:
                for admin_id in ADMIN_IDS:
                    try:
                        await _bot.send_message(
                            admin_id,
                            f"⚠️ <b>Роутер недоступен!</b>\nМодуль «Большой Брат» не смог подключиться по SSH.\n<code>{exc}</code>",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
        return

    # Get all users and their MACs
    all_users = await user_db.get_all_active_users()

    for user in all_users:
        user_macs = [m.strip().upper() for m in user["mac_addresses"].split(",") if m.strip()]
        if not user_macs:
            continue  # user hasn't registered devices yet

        is_home = any(mac in active_macs for mac in user_macs)
        result = await user_db.update_presence(user_macs[0], is_home)

        # Notify on status change
        if result:
            uid, old_status, new_status = result
            if old_status != new_status and _bot:
                if new_status == "home":
                    emoji, text = "🏠", f"<b>{user['full_name']}</b> вернулся домой!"
                else:
                    emoji, text = "🚪", f"<b>{user['full_name']}</b> ушёл из комнаты."

                # Notify admins
                for admin_id in ADMIN_IDS:
                    try:
                        await _bot.send_message(admin_id, f"{emoji} {text}", parse_mode="HTML")
                    except Exception:
                        pass
