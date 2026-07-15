"""Journal des conversations (JSONL) pour étudier le comportement du modèle.

Chaque tour écrit une ligne JSON dans data/conversation_log.jsonl :
message reçu, sortie brute du modèle, réponse, infos extraites, préférences
détectées, durée, repli éventuel. Fichier local (aucune donnée ne sort).

Analyse rapide :
  cat data/conversation_log.jsonl | python -m json.tool     (ligne par ligne)
  ou ouvrez-le dans un tableur / éditeur.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import threading
from pathlib import Path

from . import config

log = logging.getLogger(__name__)
_lock = threading.Lock()


def record(entry: dict) -> None:
    if not config.CONVERSATION_LOG:
        return
    line = {"ts": dt.datetime.now().isoformat(timespec="seconds"), **entry}
    try:
        path = Path(config.CONV_LOG_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with _lock, path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:
        log.warning("Écriture du journal de conversation impossible", exc_info=False)
