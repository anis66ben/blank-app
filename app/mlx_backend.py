"""Moteur LLM local via MLX (framework Apple Silicon), sans Ollama.

Exécute Qwen3-4B-4bit directement dans le processus Python avec `mlx-lm`.
- Aucun appel réseau : les conversations restent 100 % locales.
- Le modèle est chargé une seule fois puis gardé en mémoire.
- Génération sérialisée par un verrou (mlx-lm n'est pas thread-safe).
- Raisonnement Qwen3 désactivé via le gabarit de chat (`enable_thinking=False`).

Ce module n'importe `mlx_lm` que lorsqu'il est réellement utilisé, pour que le
reste de l'application reste importable et testable hors macOS/Apple Silicon.
"""
from __future__ import annotations

import logging
import re
import threading
import time

from . import config

log = logging.getLogger(__name__)

_lock = threading.Lock()
_model = None
_tokenizer = None
_load_error: str | None = None

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_think(text: str) -> str:
    return _THINK_RE.sub("", text or "").strip()


def is_available() -> bool:
    """Vrai si mlx-lm est importable (donc on est sur Apple Silicon)."""
    try:
        import mlx_lm  # noqa: F401
        return True
    except Exception:
        return False


def ensure_loaded():
    """Charge le modèle si nécessaire (peut prendre plusieurs secondes au 1er appel)."""
    global _model, _tokenizer, _load_error
    if _model is not None:
        return _model, _tokenizer
    with _lock:
        if _model is None and _load_error is None:
            try:
                from mlx_lm import load
                t0 = time.monotonic()
                log.info("Chargement du modèle MLX %s …", config.MLX_MODEL)
                _model, _tokenizer = load(config.MLX_MODEL)
                log.info("Modèle MLX chargé en %.1fs", time.monotonic() - t0)
            except Exception as exc:
                _load_error = str(exc)
                log.exception("Échec du chargement du modèle MLX")
                raise
    if _model is None:
        raise RuntimeError(f"Modèle MLX indisponible : {_load_error}")
    return _model, _tokenizer


def _build_prompt(tokenizer, system: str, messages: list[dict]) -> str:
    """Construit le prompt via le gabarit de chat Qwen3, raisonnement désactivé."""
    chat = ([{"role": "system", "content": system}] if system else []) + messages
    kwargs = dict(add_generation_prompt=True, tokenize=False)
    try:
        return tokenizer.apply_chat_template(chat, enable_thinking=config.MLX_THINK, **kwargs)
    except TypeError:
        # Gabarit ne connaissant pas enable_thinking : repli sur le marqueur /no_think
        if not config.MLX_THINK and chat:
            chat = [dict(m) for m in chat]
            chat[-1]["content"] = chat[-1]["content"] + " /no_think"
        return tokenizer.apply_chat_template(chat, **kwargs)


def _sampling_kwargs() -> dict:
    """Température + pénalité de répétition : indispensables pour éviter des
    réponses identiques et en boucle (la génération par défaut est déterministe).
    Tolérant aux variations d'API de mlx-lm."""
    kwargs: dict = {}
    try:
        from mlx_lm.sample_utils import make_logits_processors, make_sampler
        kwargs["sampler"] = make_sampler(temp=config.MLX_TEMP, top_p=0.95)
        kwargs["logits_processors"] = make_logits_processors(
            repetition_penalty=config.MLX_REPETITION_PENALTY,
            repetition_context_size=40)
    except Exception:
        log.debug("Échantillonnage avancé mlx-lm indisponible", exc_info=False)
    return kwargs


def generate_text(system: str, messages: list[dict], max_tokens: int | None = None) -> str:
    """Génère une réponse texte. Sérialisé pour éviter les appels concurrents."""
    model, tokenizer = ensure_loaded()
    prompt = _build_prompt(tokenizer, system, messages)
    max_tokens = max_tokens or config.MLX_MAX_TOKENS
    sampling = _sampling_kwargs()

    from mlx_lm import generate
    t0 = time.monotonic()
    with _lock:
        try:
            text = generate(model, tokenizer, prompt=prompt,
                            max_tokens=max_tokens, verbose=False, **sampling)
        except TypeError:
            # Signature de mlx-lm qui n'accepte pas sampler/logits_processors
            try:
                text = generate(model, tokenizer, prompt=prompt,
                                max_tokens=max_tokens, verbose=False)
            except TypeError:
                text = generate(model, tokenizer, prompt, max_tokens=max_tokens)
    log.info("Génération MLX en %.1fs", time.monotonic() - t0)
    return _strip_think(text)
