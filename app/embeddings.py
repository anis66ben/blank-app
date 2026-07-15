"""Embeddings locaux pour le RAG.

Trois sources possibles, choisies automatiquement :
  1. Ollama (si c'est le moteur actif) — via son endpoint /api/embed ;
  2. sentence-transformers (petit modèle local, optionnel) — pour MLX ;
  3. aucune → le RAG bascule en mode lexical (mots-clés), sans dépendance.

sentence-transformers n'est PAS dans requirements.txt (lourd). Pour activer le
RAG sémantique avec MLX :  pip install -r requirements-rag.txt
"""
from __future__ import annotations

import logging

from . import config

log = logging.getLogger(__name__)

_st_model = None
_st_tried = False


def _load_sentence_transformers():
    global _st_model, _st_tried
    if _st_tried:
        return _st_model
    _st_tried = True
    try:
        from sentence_transformers import SentenceTransformer
        log.info("Chargement du modèle d'embeddings %s …", config.EMBED_MODEL)
        _st_model = SentenceTransformer(config.EMBED_MODEL)
        log.info("Embeddings sémantiques prêts (%s)", config.EMBED_MODEL)
    except Exception:
        _st_model = None
        log.info("sentence-transformers indisponible → RAG en mode lexical "
                 "(installez requirements-rag.txt pour le sémantique)")
    return _st_model


def semantic_available() -> bool:
    """Vrai si des embeddings vectoriels sont disponibles (Ollama ou ST)."""
    from . import llm
    if llm.provider() == "ollama":
        return True
    return _load_sentence_transformers() is not None


def embed(texts: list[str]) -> list[list[float]] | None:
    """Renvoie les vecteurs, ou None si aucun backend sémantique (mode lexical)."""
    from . import llm
    if llm.provider() == "ollama":
        try:
            return llm.embed(texts)
        except Exception:
            log.warning("Embed Ollama indisponible", exc_info=False)
            return None
    model = _load_sentence_transformers()
    if model is None:
        return None
    try:
        vecs = model.encode(texts, normalize_embeddings=True)
        return [[float(x) for x in v] for v in vecs]
    except Exception:
        log.warning("Embed sentence-transformers échoué", exc_info=False)
        return None
