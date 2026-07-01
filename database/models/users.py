from database.connection import acquire


async def register_user(telegram_id: int, username: str | None, full_name: str) -> bool:
    async with acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id=$1", telegram_id
        )
        if existing:
            await conn.execute(
                "UPDATE users SET username=$1, full_name=$2 WHERE telegram_id=$3",
                username, full_name, telegram_id
            )
            return False
        await conn.execute(
            "INSERT INTO users (telegram_id, username, full_name) VALUES ($1,$2,$3)",
            telegram_id, username, full_name
        )
        return True


async def get_user(telegram_id: int):
    async with acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id=$1", telegram_id
        )


async def get_all_active_users():
    async with acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM users WHERE is_active=1 ORDER BY full_name"
        )


async def get_user_by_username(username: str):
    async with acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM users WHERE lower(username)=lower($1)", username
        )


async def add_mac_address(telegram_id: int, mac: str) -> bool:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT mac_addresses FROM users WHERE telegram_id=$1", telegram_id
        )
        if not row:
            return False
        macs = [m.strip().upper() for m in (row["mac_addresses"] or "").split(",") if m.strip()]
        mac = mac.strip().upper()
        if mac in macs:
            return False
        macs.append(mac)
        await conn.execute(
            "UPDATE users SET mac_addresses=$1 WHERE telegram_id=$2",
            ",".join(macs), telegram_id
        )
        return True


async def update_presence(mac: str, is_home: bool):
    from datetime import datetime
    now_str = datetime.now().isoformat()
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT telegram_id, mac_addresses, status FROM users WHERE is_active=1"
        )
        for row in rows:
            macs = [m.strip().upper() for m in (row["mac_addresses"] or "").split(",") if m.strip()]
            if mac.upper() in macs:
                new_status = "home" if is_home else "away"
                old_status = row["status"]
                await conn.execute(
                    "UPDATE users SET status=$1, last_seen=$2 WHERE telegram_id=$3",
                    new_status, now_str, row["telegram_id"]
                )
                return row["telegram_id"], old_status, new_status
    return None


async def get_home_users():
    async with acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM users WHERE status='home' AND is_active=1"
        )
