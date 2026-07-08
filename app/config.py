"""Configuration centrale, chargée depuis les variables d'environnement (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# --- Choix du moteur IA -----------------------------------------------------
# LLM_PROVIDER : "claude", "ollama", "none" ou "" (auto).
#   auto = ollama si OLLAMA_BASE_URL joignable, sinon claude si clé, sinon none.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()

# Claude (API payante, optionnelle)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")

# Ollama local (Qwen3 8B, gratuit et privé)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "120"))

# RAG (mémoire vectorielle : « fenêtre de contexte déportée »)
RAG_ENABLED = os.getenv("RAG_ENABLED", "auto").strip().lower()   # auto / true / false
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

_default_db = f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", _default_db)
if DATABASE_URL.startswith("sqlite:///") and not DATABASE_URL.startswith("sqlite:////"):
    # Résout les chemins SQLite relatifs par rapport à la racine du projet
    rel = DATABASE_URL[len("sqlite:///"):]
    if not Path(rel).is_absolute():
        DATABASE_URL = f"sqlite:///{BASE_DIR / rel}"

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
COMMUNITY_CHAT_ID = os.getenv("COMMUNITY_CHAT_ID", "")

# IDs Telegram des administrateurs (séparés par des virgules) : accès aux
# commandes /admin, /membres, /fiche, /matchs, /conv, /publier dans le bot.
ADMIN_TELEGRAM_IDS = {int(x) for x in os.getenv("ADMIN_TELEGRAM_IDS", "")
                      .replace(" ", "").split(",") if x.strip().lstrip("-").isdigit()}

MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", "65"))
MIN_COMPLETENESS_FOR_MATCHING = int(os.getenv("MIN_COMPLETENESS_FOR_MATCHING", "30"))

# Nombre de messages d'historique envoyés au modèle à chaque tour
CONVERSATION_WINDOW = int(os.getenv("CONVERSATION_WINDOW", "30"))
