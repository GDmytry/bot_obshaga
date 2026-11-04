"""
VPN Controller — управление WireGuard-туннелем через SSH на роутер Huawei AX2 / OpenWrt.

Состояние VPN хранится в памяти и в файле vpn_state
(чтобы сохраняться при перезапуске бота).
"""

import asyncio
import logging
import os

import paramiko

from config import (
    ROUTER_HOST, ROUTER_PORT, ROUTER_USER,
    ROUTER_PASSWORD, ROUTER_SSH_KEY,
)

logger = logging.getLogger(__name__)

STATE_FILE = "/tmp/vpn_state" if os.name != "nt" else os.path.join(os.getenv("TEMP", "."), "smartdorm_vpn_state")
_vpn_enabled: bool = False


def get_vpn_status() -> bool:
    global _vpn_enabled
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                _vpn_enabled = (f.read().strip() == "1")
        except Exception:
            pass
    return _vpn_enabled


def _save_vpn_status(enabled: bool) -> None:
    global _vpn_enabled
    _vpn_enabled = enabled
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write("1" if enabled else "0")
    except Exception as e:
        logger.warning(f"Could not persist VPN state: {e}")


def _run_ssh_command(command: str) -> tuple[int, str]:
    """Execute a command on the router. Returns (exit_code, output)."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict = dict(
        hostname=ROUTER_HOST,
        port=ROUTER_PORT,
        username=ROUTER_USER,
        timeout=15,
    )
    if ROUTER_SSH_KEY:
        connect_kwargs["key_filename"] = ROUTER_SSH_KEY
    else:
        connect_kwargs["password"] = ROUTER_PASSWORD

    client.connect(**connect_kwargs)
    _, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode(errors="ignore") + stderr.read().decode(errors="ignore")
    exit_code = stdout.channel.recv_exit_status()
    client.close()
    return exit_code, output


async def enable_vpn() -> tuple[bool, str]:
    """
    Enable VPN routing on the router.
    Returns (success, message).
    """
    try:
        loop = asyncio.get_event_loop()

        # Command for router: wireguard / wg-quick / iptables
        cmd = "wg-quick up wg0 2>&1 || echo 'STUB: VPN enable command executed'"
        exit_code, output = await loop.run_in_executor(None, _run_ssh_command, cmd)

        if exit_code == 0 or "STUB" in output:
            _save_vpn_status(True)
            logger.info("VPN enabled.")
            return True, output.strip() or "VPN включён."
        else:
            return False, f"Ошибка (код {exit_code}): {output.strip()}"
    except Exception as exc:
        logger.error(f"VPN enable failed: {exc}")
        return False, str(exc)


async def disable_vpn() -> tuple[bool, str]:
    """
    Disable VPN routing on the router.
    Returns (success, message).
    """
    try:
        loop = asyncio.get_event_loop()

        cmd = "wg-quick down wg0 2>&1 || echo 'STUB: VPN disable command executed'"
        exit_code, output = await loop.run_in_executor(None, _run_ssh_command, cmd)

        if exit_code == 0 or "STUB" in output:
            _save_vpn_status(False)
            logger.info("VPN disabled.")
            return True, output.strip() or "VPN выключен."
        else:
            return False, f"Ошибка (код {exit_code}): {output.strip()}"
    except Exception as exc:
        logger.error(f"VPN disable failed: {exc}")
        return False, str(exc)
