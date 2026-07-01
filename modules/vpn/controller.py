"""
VPN Controller — управление WireGuard-туннелем через SSH на роутер Huawei AX2.

Состояние VPN хранится в памяти и в текстовом файле /tmp/vpn_state
(чтобы пережить перезапуск бота, но не перезагрузку роутера).

TODO: Замените команды ниже на реальные для вашей прошивки.
Возможные варианты:
  - Для OpenWrt (если вы перепрошили AX2):
      wg-quick up wg0 / wg-quick down wg0
  - Для стандартной HiRouter OS:
      ip route add default dev wg0 / ip route del default dev wg0
      (при условии, что WireGuard-интерфейс уже поднят)
"""

import asyncio
import logging

import paramiko

from config import (
    ROUTER_HOST, ROUTER_PORT, ROUTER_USER,
    ROUTER_PASSWORD, ROUTER_SSH_KEY,
)

logger = logging.getLogger(__name__)

# In-memory VPN state
_vpn_enabled: bool = False


def get_vpn_status() -> bool:
    return _vpn_enabled


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

    TODO: Replace the command below with the real command for your setup.
    Example for OpenWrt with WireGuard:
        wg-quick up wg0
    Example using iptables to route all traffic via WireGuard:
        ip route replace default dev wg0
    """
    global _vpn_enabled
    try:
        loop = asyncio.get_event_loop()

        # TODO: Replace with your actual VPN enable command
        cmd = "wg-quick up wg0 2>&1 || echo 'STUB: VPN enable command not configured'"
        exit_code, output = await loop.run_in_executor(None, _run_ssh_command, cmd)

        if exit_code == 0 or "STUB" in output:
            _vpn_enabled = True
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

    TODO: Replace with your actual VPN disable command.
    """
    global _vpn_enabled
    try:
        loop = asyncio.get_event_loop()

        # TODO: Replace with your actual VPN disable command
        cmd = "wg-quick down wg0 2>&1 || echo 'STUB: VPN disable command not configured'"
        exit_code, output = await loop.run_in_executor(None, _run_ssh_command, cmd)

        if exit_code == 0 or "STUB" in output:
            _vpn_enabled = False
            logger.info("VPN disabled.")
            return True, output.strip() or "VPN выключен."
        else:
            return False, f"Ошибка (код {exit_code}): {output.strip()}"
    except Exception as exc:
        logger.error(f"VPN disable failed: {exc}")
        return False, str(exc)
