import os
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from database.models import queues as q_db
from database.models import users as user_db
from database.models import finance as fin_db
from database.models.discipline import get_all_restrictions, get_all_active_warnings
from modules.vpn.controller import get_vpn_status

app = FastAPI(title="Smart-Общага 502 API")


def fmt_dt(value, fmt: str = "%d.%m %H:%M") -> str:
    """Format a date that may be a datetime object (postgres) or ISO string (sqlite dev mode)."""
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime(fmt)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Expose Prometheus metrics at /metrics
Instrumentator().instrument(app).expose(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")


# ── Presence ──────────────────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    all_users = await user_db.get_all_active_users()
    residents = [
        {
            "id": u["telegram_id"],
            "name": u["full_name"],
            "status": u["status"],
            "last_seen": u["last_seen"].isoformat() if u["last_seen"] else None,
        }
        for u in all_users
    ]
    return {
        "residents": residents,
        "vpn_enabled": get_vpn_status(),
        "home_count": sum(1 for r in residents if r["status"] == "home"),
    }


# ── Finance ───────────────────────────────────────────────────────────────

@app.get("/api/finance")
async def api_finance():
    expenses = await fin_db.get_all_expenses(limit=20)
    balances = await fin_db.compute_balances()
    all_users = await user_db.get_all_active_users()

    name_map = {u["telegram_id"]: u["full_name"] for u in all_users}

    debts = [
        {
            "debtor": name_map.get(debtor, f"ID:{debtor}"),
            "creditor": name_map.get(creditor, f"ID:{creditor}"),
            "amount": float(amt),
        }
        for (debtor, creditor), amt in sorted(balances.items(), key=lambda x: -x[1])
    ]

    expense_list = [
        {
            "payer": e["payer_name"],
            "amount": float(e["amount"]),
            "description": e["description"],
            "date": fmt_dt(e["created_at"]),
        }
        for e in expenses
    ]

    return {"debts": debts, "expenses": expense_list}


# ── Discipline ────────────────────────────────────────────────────────────

@app.get("/api/discipline")
async def api_discipline():
    restrictions = await get_all_restrictions()
    warnings = await get_all_active_warnings()

    restriction_list = [
        {
            "user": r["full_name"],
            "type": r["type"],
            "reason": r["reason"],
            "expires_at": fmt_dt(r["expires_at"]),
        }
        for r in restrictions
    ]

    warn_list = [
        {
            "user": w["full_name"],
            "reason": w["reason"],
            "date": fmt_dt(w["created_at"]),
        }
        for w in warnings
    ]

    return {"restrictions": restriction_list, "warnings": warn_list}


# ── Queues (Mini App compatibility) ──────────────────────────────────────

@app.get("/api/queues")
async def api_queues(chat_id: int):
    queues = await q_db.get_all_queues(chat_id)
    result = []
    for q in queues:
        members = await q_db.get_queue_members(q["id"])
        result.append({
            "id": q["id"],
            "name": q["name"],
            "members": [
                {
                    "id": m["user_id"],
                    "name": m["user_name"],
                    "order": m["order_index"],
                    "is_done": m["is_done"],
                    "done_time": m["done_time"],
                }
                for m in members
            ],
        })
    return {"queues": result}
