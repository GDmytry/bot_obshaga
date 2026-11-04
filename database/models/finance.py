from database.connection import acquire
from modules.finance.calculator import (
    split_expense_amount,
    compute_net_debts,
    get_user_breakdown,
)


async def add_expense(payer_id: int, amount, description: str, split_with: list[int]) -> int:
    share, splits = split_expense_amount(float(amount), payer_id, split_with)
    async with acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO expenses (payer_id, amount, description) VALUES ($1,$2,$3) RETURNING id",
            payer_id, float(amount), description
        )
        expense_id = row["id"]
        for sp in splits:
            await conn.execute(
                "INSERT INTO expense_splits (expense_id, debtor_id, amount) VALUES ($1,$2,$3)",
                expense_id, sp["debtor_id"], sp["amount"]
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
    return compute_net_debts([dict(r) for r in rows])


async def get_user_balance(telegram_id: int) -> dict:
    balances = await compute_balances()
    return get_user_breakdown(balances, telegram_id)
