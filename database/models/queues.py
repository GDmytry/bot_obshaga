from database.connection import acquire


async def create_queue(chat_id: int, name: str) -> int | None:
    async with acquire() as conn:
        try:
            row = await conn.fetchrow(
                "INSERT INTO queues (chat_id, name) VALUES ($1, $2) RETURNING id",
                chat_id, name
            )
            return row["id"] if row else None
        except Exception:
            return None


async def get_queue(chat_id: int, name: str):
    async with acquire() as conn:
        return await conn.fetchrow(
            "SELECT id, name, current_user_index FROM queues WHERE chat_id=$1 AND name=$2",
            chat_id, name
        )


async def get_queue_by_id(queue_id: int):
    async with acquire() as conn:
        return await conn.fetchrow(
            "SELECT id, name, current_user_index, chat_id FROM queues WHERE id=$1",
            queue_id
        )


async def get_all_queues(chat_id: int):
    async with acquire() as conn:
        return await conn.fetch(
            "SELECT id, name, current_user_index FROM queues WHERE chat_id=$1",
            chat_id
        )


async def join_queue(queue_id: int, user_id: int, user_name: str) -> bool:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(MAX(order_index), -1) AS mx FROM queue_members WHERE queue_id=$1",
            queue_id
        )
        next_index = (row["mx"] if row and row["mx"] is not None else -1) + 1
        try:
            await conn.execute(
                "INSERT INTO queue_members (queue_id, user_id, user_name, order_index) VALUES ($1,$2,$3,$4)",
                queue_id, user_id, user_name, next_index
            )
            return True
        except Exception:
            return False


async def leave_queue(queue_id: int, user_id: int) -> bool:
    async with acquire() as conn:
        result = await conn.execute(
            "DELETE FROM queue_members WHERE queue_id=$1 AND user_id=$2",
            queue_id, user_id
        )
        deleted = int(str(result).split()[-1]) if result else 0
        if not deleted:
            return False
        rows = await conn.fetch(
            "SELECT id FROM queue_members WHERE queue_id=$1 ORDER BY order_index ASC",
            queue_id
        )
        for new_idx, row in enumerate(rows):
            await conn.execute(
                "UPDATE queue_members SET order_index=$1 WHERE id=$2",
                new_idx, row["id"]
            )
        return True


async def get_queue_members(queue_id: int):
    async with acquire() as conn:
        return await conn.fetch(
            "SELECT user_id, user_name, order_index, is_done, done_time "
            "FROM queue_members WHERE queue_id=$1 ORDER BY order_index ASC",
            queue_id
        )


async def mark_done(queue_id: int, user_id: int) -> bool:
    from datetime import datetime
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT is_done FROM queue_members WHERE queue_id=$1 AND user_id=$2",
            queue_id, user_id
        )
        if not row or row["is_done"]:
            return False
        now_str = datetime.now().strftime("%H:%M")
        await conn.execute(
            "UPDATE queue_members SET is_done=1, done_time=$1 WHERE queue_id=$2 AND user_id=$3",
            now_str, queue_id, user_id
        )
        return True


async def unmark_done(queue_id: int, user_id: int) -> bool:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT is_done FROM queue_members WHERE queue_id=$1 AND user_id=$2",
            queue_id, user_id
        )
        if not row or not row["is_done"]:
            return False
        await conn.execute(
            "UPDATE queue_members SET is_done=0, done_time=NULL WHERE queue_id=$1 AND user_id=$2",
            queue_id, user_id
        )
        return True
