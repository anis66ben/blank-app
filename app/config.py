"""Configuration centrale, chargée depuis les variables d'environnement (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# --- Choix du moteur IA -----------------------------------------------------
# LLM_PROVIDER : "mlx" (local Apple Silicon), "ollama", "claude", "none" ou "" (auto).
#   auto = claude si clé, sinon ollama si joignable, sinon none.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()

# Claude (API payante, optionnelle)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")

# MLX local (Qwen3 4B 4-bit, Apple Silicon — gratuit et privé, sans Ollama)
MLX_MODEL = os.getenv("MLX_MODEL", "mlx-community/Qwen3-4B-4bit")
MLX_MAX_TOKENS = int(os.getenv("MLX_MAX_TOKENS", "400"))
MLX_THINK = os.getenv("MLX_THINK", "false").strip().lower() == "true"
# Variété des réponses : température > 0 évite les réponses identiques en boucle ;
# la pénalité de répétition empêche le modèle de se répéter.
MLX_TEMP = float(os.getenv("MLX_TEMP", "0.7"))
MLX_REPETITION_PENALTY = float(os.getenv("MLX_REPETITION_PENALTY", "1.15"))

# Ollama local (alternative à MLX)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "180"))
# Raisonnement Qwen3 : désactivé par défaut (bien plus rapide). true pour l'activer.
OLLAMA_THINK = os.getenv("OLLAMA_THINK", "false").strip().lower() == "true"
# Maintient le modèle chargé en mémoire (évite le rechargement à chaque message).
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

# RAG (mémoire déportée hors du prompt). auto/true = actif pour mlx/ollama.
RAG_ENABLED = os.getenv("RAG_ENABLED", "auto").strip().lower()   # auto / true / false
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
# Modèle d'embeddings pour le RAG sémantique avec MLX (optionnel, multilingue).
# Sans lui, le RAG fonctionne en mode lexical (mots-clés). Voir requirements-rag.txt.
EMBED_MODEL = os.getenv("EMBED_MODEL",
                        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

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

# Pondérations du matching (ajustables sans toucher au code). La somme fait 100 ;
# les critères recherchés explicites ajoutent un bonus/malus (±16) par-dessus.
MATCH_WEIGHTS = {
    "pratique_religieuse": float(os.getenv("MATCH_W_RELIGION", "25")),
    "projet_famille": float(os.getenv("MATCH_W_FAMILY", "20")),
    "localisation": float(os.getenv("MATCH_W_LOCATION", "15")),
    "personnalite": float(os.getenv("MATCH_W_PERSONALITY", "10")),
    "centres_interet": float(os.getenv("MATCH_W_INTERESTS", "18")),
    "habitudes_vie": float(os.getenv("MATCH_W_LIFESTYLE", "7")),
    "proximite_age": float(os.getenv("MATCH_W_AGE", "5")),
}

# Nombre de messages d'historique envoyés au modèle à chaque tour
CONVERSATION_WINDOW = int(os.getenv("CONVERSATION_WINDOW", "30"))
# Fenêtre d'historique pour les petits modèles locaux (mlx) : plus courte que
# Claude pour rester rapide et net, complétée par la mémoire persistante
# (portrait + préférences, toujours réinjectés).
LOCAL_HISTORY_WINDOW = int(os.getenv("LOCAL_HISTORY_WINDOW", "14"))

# Journal des conversations (pour étudier le comportement du modèle).
CONVERSATION_LOG = os.getenv("CONVERSATION_LOG", "true").strip().lower() == "true"
CONV_LOG_PATH = os.getenv("CONV_LOG_PATH", str(BASE_DIR / "data" / "conversation_log.jsonl"))

# RGPD : exiger le consentement au /start avant toute conversation.
CONSENT_REQUIRED = os.getenv("CONSENT_REQUIRED", "true").strip().lower() == "true"

# Plafond d'appels IA par membre et par jour (maîtrise des coûts + anti-flood).
MAX_MESSAGES_PER_DAY = int(os.getenv("MAX_MESSAGES_PER_DAY", "40"))
