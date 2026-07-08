"""RAG local : mémoire vectorielle pour déporter la fenêtre de contexte.

Au lieu d'envoyer tout l'historique au modèle à chaque tour, on indexe les
souvenirs (faits, réactions, préférences, échanges) sous forme de vecteurs, et
on ne réinjecte dans le prompt que les `RAG_TOP_K` souvenirs les plus proches
du message courant. Le contexte « vit » donc dans la base, pas dans le prompt.

Embeddings via Ollama ; similarité cosinus calculée en Python (aucune
dépendance lourde type FAISS). Volumétrie adaptée à une communauté Telegram.
"""
from __future__ import annotations

import logging
import math

from . import config, llm
from .db import MemoryChunk

log = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def index_text(session, user_id: int, kind: str, text: str) -> bool:
    """Indexe un souvenir. Évite les doublons exacts récents. Silencieux en cas
    d'erreur (le RAG est un bonus, jamais un point de blocage)."""
    text = (text or "").strip()
    if not text or not llm.rag_enabled():
        return False
    exists = (session.query(MemoryChunk)
              .filter(MemoryChunk.user_id == user_id, MemoryChunk.text == text)
              .first())
    if exists:
        return False
    try:
        vec = llm.embed([text])[0]
    except Exception:
        log.warning("Embedding indisponible, souvenir non indexé", exc_info=False)
        return False
    session.add(MemoryChunk(user_id=user_id, kind=kind, text=text, embedding=vec))
    return True


def retrieve(session, user_id: int, query: str, k: int | None = None) -> list[str]:
    """Renvoie les k souvenirs les plus pertinents pour `query`."""
    if not query or not llm.rag_enabled():
        return []
    k = k or config.RAG_TOP_K
    rows = session.query(MemoryChunk).filter(MemoryChunk.user_id == user_id).all()
    if not rows:
        return []
    try:
        qvec = llm.embed([query])[0]
    except Exception:
        return []
    scored = [(_cosine(qvec, r.embedding or []), r.text) for r in rows]
    scored.sort(key=lambda t: t[0], reverse=True)
    # ne garde que les souvenirs raisonnablement proches
    return [text for score, text in scored[:k] if score > 0.25]


def context_block(session, user_id: int, query: str) -> str:
    """Bloc de souvenirs pertinents à insérer dans le prompt système."""
    chunks = retrieve(session, user_id, query)
    if not chunks:
        return ""
    body = "\n".join(f"- {c}" for c in chunks)
    return ("\nSOUVENIRS PERTINENTS (mémoire à long terme de ce membre, "
            f"récupérés pour ce message) :\n{body}\n")
