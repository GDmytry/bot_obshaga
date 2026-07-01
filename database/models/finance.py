from decimal import Decimal
from database.connection import acquire


async def add_expense(payer_id: int, amount, description: str, split_with: list[int]) -> int:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO expenses (payer_id, amount, description) VALUES ($1,$2,$3) RETURNING id",
            payer_id, float(amount), description
        )
        expense_id = row["id"]
        num_people = len(split_with)
        share = round(float(amount) / num_people, 2)
        for uid in split_with:
            if uid != payer_id:
                await conn.execute(
                    "INSERT INTO expense_splits (expense_id, debtor_id, amount) VALUES ($1,$2,$3)",
                    expense_id, uid, share
                )
        return expense_id


async def get_all_expenses(limit: int = 50):
    async with acquire() as conn:
        return await conn.fetch(
            "SELECT e.id, e.payer_id, u.full_name as payer_name, e.amount, e.description, e.created_at "
            "FROM expenses e JOIN users u ON e.payer_id=u.telegram_id "
            "ORDER BY e.created_at DESC LIMIT $1",
            limit
        )


async def compute_balances() -> dict:
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT es.debtor_id, e.payer_id AS creditor_id, SUM(es.amount) AS total "
            "FROM expense_splits es "
            "JOIN expenses e ON e.id = es.expense_id "
            "GROUP BY es.debtor_id, e.payer_id"
        )

    raw: dict = {}
    for row in rows:
        key = (row["debtor_id"], row["creditor_id"])
        raw[key] = raw.get(key, 0.0) + float(row["total"])

    netted: dict = {}
    processed = set()
    for (a, b), amt_ab in raw.items():
        if (a, b) in processed:
            continue
        amt_ba = raw.get((b, a), 0.0)
        net = amt_ab - amt_ba
        if net > 0.005:
            netted[(a, b)] = round(net, 2)
        elif net < -0.005:
            netted[(b, a)] = round(-net, 2)
        processed.add((a, b))
        processed.add((b, a))

    return netted


async def get_user_balance(telegram_id: int) -> dict:
    balances = await compute_balances()
    owed_by: dict = {}
    owe_to: dict = {}
    for (debtor, creditor), amt in balances.items():
        if creditor == telegram_id:
            owed_by[debtor] = owed_by.get(debtor, 0.0) + amt
        if debtor == telegram_id:
            owe_to[creditor] = owe_to.get(creditor, 0.0) + amt
    return {"owed_by": owed_by, "owe_to": owe_to}
