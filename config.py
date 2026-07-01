import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────── Telegram Bot ────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
PROXY_URL: str | None = os.getenv("PROXY_URL")
# Comma-separated list of Telegram user IDs that have admin rights
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]

# ──────────────────────── Web App ─────────────────────────────
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")
MINI_APP_LINK: str = os.getenv("MINI_APP_LINK", "")

# ──────────────────────── PostgreSQL ──────────────────────────
DB_HOST: str = os.getenv("DB_HOST", "db")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_NAME: str = os.getenv("DB_NAME", "smartdorm")
DB_USER: str = os.getenv("DB_USER", "smartdorm")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "changeme")

DB_DSN: str = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ──────────────────────── Router SSH ──────────────────────────
ROUTER_HOST: str = os.getenv("ROUTER_HOST", "192.168.3.1")
ROUTER_PORT: int = int(os.getenv("ROUTER_PORT", "22"))
ROUTER_USER: str = os.getenv("ROUTER_USER", "root")
ROUTER_PASSWORD: str = os.getenv("ROUTER_PASSWORD", "")
# SSH key path (preferred over password)
ROUTER_SSH_KEY: str = os.getenv("ROUTER_SSH_KEY", "")

# ──────────────────────── Discipline ──────────────────────────
# Number of warns before automatic restriction is triggered
WARN_LIMIT: int = int(os.getenv("WARN_LIMIT", "3"))
# Hours until restriction is automatically lifted
RESTRICTION_HOURS: int = int(os.getenv("RESTRICTION_HOURS", "24"))
# Max debt (RUB) before auto-warn is issued
MAX_DEBT_LIMIT: float = float(os.getenv("MAX_DEBT_LIMIT", "500.0"))

# ──────────────────────── Validation ─────────────────────────
if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
    raise ValueError(
        "❌ BOT_TOKEN not found! Set it in your .env file."
    )
