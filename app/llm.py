"""Couche d'abstraction du moteur IA.

Expose une interface unique quel que soit le fournisseur :
  - chat_structured(system, messages, model_cls) -> instance Pydantic
  - chat_text(prompt) -> str
  - embed(texts) -> list[list[float]]   (pour le RAG ; Ollama uniquement)

Fournisseurs pris en charge :
  - "claude"  : API Anthropic (payante)
  - "ollama"  : modèle local via Ollama (Qwen3 8B, gratuit et privé)
  - "none"    : aucun LLM -> le bot bascule sur le questionnaire guidé
"""
from __future__ import annotations

import json
import logging
import re
from typing import Type, TypeVar

from pydantic import BaseModel

from . import config

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_ollama_ok: bool | None = None


def _strip_think(text: str) -> str:
    """Retire les blocs de raisonnement <think>…</think> des modèles Qwen3."""
    return _THINK_RE.sub("", text or "").strip()


def _ollama_reachable() -> bool:
    global _ollama_ok
    if _ollama_ok is None:
        try:
            import httpx
            r = httpx.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=3)
            _ollama_ok = r.status_code == 200
        except Exception:
            _ollama_ok = False
    return _ollama_ok


def provider() -> str:
    """Fournisseur actif, selon la config puis l'auto-détection."""
    if config.LLM_PROVIDER in ("claude", "ollama", "none"):
        return config.LLM_PROVIDER
    # auto
    if config.ANTHROPIC_API_KEY:
        return "claude"
    if _ollama_reachable():
        return "ollama"
    return "none"


def enabled() -> bool:
    return provider() in ("claude", "ollama")


def rag_enabled() -> bool:
    """Le RAG nécessite des embeddings : disponible avec Ollama."""
    if config.RAG_ENABLED == "false":
        return False
    if config.RAG_ENABLED == "true":
        return provider() == "ollama"
    return provider() == "ollama"      # auto


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------
def _ollama_post(path: str, body: dict) -> dict:
    import httpx
    r = httpx.post(f"{config.OLLAMA_BASE_URL}{path}", json=body,
                   timeout=config.LLM_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _ollama_chat(system: str, messages: list[dict], fmt: dict | None) -> str:
    body = {
        "model": config.OLLAMA_MODEL,
        "messages": ([{"role": "system", "content": system}] if system else []) + messages,
        "stream": False,
        "think": False,                       # désactive le raisonnement Qwen3
        "options": {"temperature": 0.7, "num_ctx": config.OLLAMA_NUM_CTX},
    }
    if fmt is not None:
        body["format"] = fmt
    data = _ollama_post("/api/chat", body)
    return _strip_think(data.get("message", {}).get("content", ""))


# ---------------------------------------------------------------------------
# Claude
# ---------------------------------------------------------------------------
_claude_client = None


def _claude():
    global _claude_client
    if _claude_client is None:
        import anthropic
        _claude_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY or None)
    return _claude_client


# ---------------------------------------------------------------------------
# Interface publique
# ---------------------------------------------------------------------------
def chat_structured(system: str, messages: list[dict], model_cls: Type[T]) -> T:
    """Réponse structurée validée contre un modèle Pydantic.

    En cas d'échec du format structuré (fréquent avec un petit modèle local),
    replie sur une réponse texte simple encapsulée : le champ nommé dans
    `_TEXT_FALLBACK_FIELD` reçoit le texte, les autres champs restent vides.
    Garantit que le bot répond toujours quelque chose."""
    prov = provider()
    if prov == "claude":
        resp = _claude().messages.parse(
            model=config.CLAUDE_MODEL, max_tokens=2048,
            system=[{"type": "text", "text": system}],
            messages=messages, output_format=model_cls)
        out = resp.parsed_output
        if out is None:
            raise RuntimeError("Réponse Claude non structurée")
        return out

    if prov == "ollama":
        schema = model_cls.model_json_schema()
        raw = _ollama_chat(system, messages, fmt=schema)
        try:
            data = json.loads(raw)
            return model_cls.model_validate(data)
        except Exception:
            log.warning("Sortie structurée Ollama invalide, repli texte simple : %.200s", raw)
            return _text_fallback(model_cls, raw or _plain_reply(system, messages))

    raise RuntimeError("Aucun fournisseur IA actif")


def chat_text(prompt: str) -> str:
    """Génération de texte libre (présentation de profil, contenu communautaire)."""
    prov = provider()
    if prov == "claude":
        resp = _claude().messages.create(
            model=config.CLAUDE_MODEL, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}])
        return next((b.text for b in resp.content if b.type == "text"), "").strip()
    if prov == "ollama":
        return _ollama_chat("", [{"role": "user", "content": prompt}], fmt=None)
    raise RuntimeError("Aucun fournisseur IA actif")


def embed(texts: list[str]) -> list[list[float]]:
    """Vecteurs d'embedding (RAG). Ollama uniquement."""
    if provider() != "ollama":
        raise RuntimeError("Embeddings disponibles uniquement avec Ollama")
    data = _ollama_post("/api/embed",
                        {"model": config.OLLAMA_EMBED_MODEL, "input": texts})
    return data.get("embeddings", [])


# ---------------------------------------------------------------------------
def _plain_reply(system: str, messages: list[dict]) -> str:
    """Dernier recours : une réponse texte sans contrainte de format."""
    try:
        return _ollama_chat(system, messages, fmt=None)
    except Exception:
        return ("Je te remercie pour ta réponse. Continuons tranquillement notre "
                "conversation, raconte-moi un peu plus si tu veux.")


def _text_fallback(model_cls: Type[T], text: str) -> T:
    """Construit une instance minimale du modèle avec le texte comme réponse."""
    payload: dict = {}
    for name, field in model_cls.model_fields.items():
        if name in ("reply", "text", "message"):
            payload[name] = _strip_think(text)[:1500] or "D'accord, je t'écoute."
    try:
        return model_cls.model_validate(payload)
    except Exception:
        # le modèle exige d'autres champs : on tente avec les valeurs par défaut
        return model_cls.model_construct(**payload)
