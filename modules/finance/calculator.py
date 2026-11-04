"""
Finance Calculator — алгоритмы расчета взаиморасчетов и долгов («Умный Общак»).
"""

from decimal import Decimal, ROUND_HALF_UP


def split_expense_amount(amount: float, payer_id: int, split_with: list[int]) -> tuple[float, list[dict]]:
    """
    Разделяет сумму расхода поровну между участниками.
    Возвращает (доля_каждого, список сплитов [{debtor_id, amount}]).
    """
    if not split_with:
        return 0.0, []

    dec_amount = Decimal(str(amount))
    count = Decimal(len(split_with))
    share = (dec_amount / count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    share_float = float(share)

    splits = []
    for uid in split_with:
        if uid != payer_id:
            splits.append({
                "debtor_id": uid,
                "amount": share_float
            })

    return share_float, splits


def compute_net_debts(raw_rows: list[dict]) -> dict[tuple[int, int], float]:
    """
    Принимает строки вида:
      [{'debtor_id': 1, 'creditor_id': 2, 'total': 150.0}, ...]
    И выполняет взаимозачёт (netting):
    Если A должен B 100 руб, а B должен A 40 руб -> A должен B 60 руб.
    Возвращает dict с ключом (debtor_id, creditor_id) -> net_amount.
    """
    raw: dict[tuple[int, int], float] = {}
    for row in raw_rows:
        debtor = int(row["debtor_id"])
        creditor = int(row["creditor_id"])
        key = (debtor, creditor)
        raw[key] = raw.get(key, 0.0) + float(row["total"])

    netted: dict[tuple[int, int], float] = {}
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


def get_user_breakdown(balances: dict[tuple[int, int], float], user_id: int) -> dict:
    """
    Возвращает разбивку для конкретного пользователя:
    кто должен ему, и кому должен он.
    """
    owed_by: dict[int, float] = {}
    owe_to: dict[int, float] = {}

    for (debtor, creditor), amt in balances.items():
        if creditor == user_id:
            owed_by[debtor] = round(owed_by.get(debtor, 0.0) + amt, 2)
        if debtor == user_id:
            owe_to[creditor] = round(owe_to.get(creditor, 0.0) + amt, 2)

    return {
        "owed_by": owed_by,  # Мне должны
        "owe_to": owe_to,    # Я должен
        "total_credit": sum(owed_by.values()),
        "total_debt": sum(owe_to.values()),
    }


def find_debtors_over_limit(balances: dict[tuple[int, int], float], limit: float) -> list[dict]:
    """
    Находит должников, суммарный долг которых превышает limit.
    """
    user_debts: dict[int, float] = {}
    for (debtor, _), amt in balances.items():
        user_debts[debtor] = user_debts.get(debtor, 0.0) + amt

    overdue = []
    for uid, total_debt in user_debts.items():
        if total_debt >= limit:
            overdue.append({
                "user_id": uid,
                "total_debt": round(total_debt, 2),
                "limit": limit
            })
    return overdue

