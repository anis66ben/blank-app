"""Configuration centrale, chargée depuis les variables d'environnement (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")

_default_db = f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", _default_db)
if DATABASE_URL.startswith("sqlite:///") and not DATABASE_URL.startswith("sqlite:////"):
    # Résout les chemins SQLite relatifs par rapport à la racine du projet
    rel = DATABASE_URL[len("sqlite:///"):]
    if not Path(rel).is_absolute():
        DATABASE_URL = f"sqlite:///{BASE_DIR / rel}"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
COMMUNITY_CHAT_ID = os.getenv("COMMUNITY_CHAT_ID", "")

MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", "65"))
MIN_COMPLETENESS_FOR_MATCHING = int(os.getenv("MIN_COMPLETENESS_FOR_MATCHING", "30"))

# Nombre de messages d'historique envoyés au modèle à chaque tour
CONVERSATION_WINDOW = int(os.getenv("CONVERSATION_WINDOW", "30"))
