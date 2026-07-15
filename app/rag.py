"""RAG local : mémoire déportée hors du prompt.

La mémoire du membre (faits, réactions, préférences, échanges marquants) vit dans
la table `memory_chunks`, PAS dans le prompt. À chaque message, on ne réinjecte
que les `RAG_TOP_K` souvenirs les plus pertinents pour ce qui vient d'être dit.

Deux modes de pertinence, choisis automatiquement :
  - SÉMANTIQUE : si des embeddings sont disponibles (Ollama, ou
    sentence-transformers installé) → similarité cosinus.
  - LEXICAL : sinon → recouvrement de mots-clés (aucune dépendance).

Le mode lexical fonctionne partout et tout de suite ; le sémantique est plus fin
(comprend les reformulations). Dans les deux cas, la mémoire est bien déportée.
"""
from __future__ import annotations

import logging
import math
import re
import unicodedata

from . import config, embeddings, llm
from .db import MemoryChunk

log = logging.getLogger(__name__)

_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "a", "à",
    "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "que", "qui", "quoi",
    "pour", "dans", "sur", "avec", "sans", "mon", "ma", "mes", "ton", "ta",
    "son", "sa", "ses", "ce", "cette", "est", "suis", "es", "en", "au", "aux",
    "pas", "plus", "moins", "très", "bien", "aussi", "dit", "avais", "avait",
}


def enabled() -> bool:
    """RAG actif pour les moteurs locaux (mlx/ollama). Désactivable via .env."""
    if config.RAG_ENABLED == "false":
        return False
    return llm.provider() in ("mlx", "ollama")


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _stem(w: str) -> str:
    """Racinisation légère : préfixe de 5 lettres, pour rapprocher les formes
    fléchies en français (famille/familial, voyage/voyages, sport/sportif)."""
    return w[:5] if len(w) > 5 else w


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{3,}", _norm(text))
    return {_stem(w) for w in words if w not in _STOPWORDS}


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def _lexical_score(q: set[str], text: str) -> float:
    d = _tokens(text)
    if not q or not d:
        return 0.0
    return len(q & d) / math.sqrt(len(q) * len(d))


# ---------------------------------------------------------------------------
# Indexation & récupération
# ---------------------------------------------------------------------------
def index_text(session, user_id: int, kind: str, text: str) -> bool:
    """Ajoute un souvenir à la mémoire (avec embedding si disponible).
    Silencieux en cas d'erreur (le RAG est un bonus, jamais un point de blocage)."""
    text = (text or "").strip()
    if not text or not enabled():
        return False
    exists = (session.query(MemoryChunk)
              .filter(MemoryChunk.user_id == user_id, MemoryChunk.text == text)
              .first())
    if exists:
        return False
    vec = None
    vectors = embeddings.embed([text])
    if vectors:
        vec = vectors[0]
    session.add(MemoryChunk(user_id=user_id, kind=kind, text=text, embedding=vec))
    return True


def retrieve(session, user_id: int, query: str, k: int | None = None) -> list[str]:
    """Renvoie les k souvenirs les plus pertinents pour `query`."""
    if not query or not enabled():
        return []
    k = k or config.RAG_TOP_K
    rows = session.query(MemoryChunk).filter(MemoryChunk.user_id == user_id).all()
    if not rows:
        return []

    qvecs = embeddings.embed([query])
    if qvecs and all(r.embedding for r in rows):
        # Mode sémantique
        qv = qvecs[0]
        scored = [(_cosine(qv, r.embedding), r.text) for r in rows]
        threshold = 0.25
    else:
        # Mode lexical
        qtok = _tokens(query)
        scored = [(_lexical_score(qtok, r.text), r.text) for r in rows]
        threshold = 0.10

    scored.sort(key=lambda t: t[0], reverse=True)
    return [text for score, text in scored[:k] if score > threshold]


def context_block(session, user_id: int, query: str) -> str:
    """Bloc de souvenirs pertinents à insérer dans le prompt (mémoire déportée)."""
    chunks = retrieve(session, user_id, query)
    if not chunks:
        return ""
    body = "\n".join(f"- {c}" for c in chunks)
    return ("\nSOUVENIRS PERTINENTS (mémoire à long terme de ce membre, "
            f"retrouvée pour ce message) :\n{body}\n")
