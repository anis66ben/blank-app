"""Gestion de la mémoire structurée des préférences (charte IA §9-11).

Règle centrale (§10) : jamais de conclusion définitive sur une seule réaction.
- 1re observation  -> hypothèse faible   (confiance 35 %)
- 2e observation   -> hypothèse renforcée (confiance 60 %) — utilisable en matching
- observations suivantes -> +12 % jusqu'à 95 % maximum
- signal contradictoire  -> la confiance retombe, l'orientation bascule si répété
"""
from __future__ import annotations

import unicodedata

from .db import Preference

DIMENSIONS = {"valeurs", "vision_couple", "personnalite", "mode_de_vie", "preference_profil"}
ORIENTATIONS = {"favorable", "defavorable", "reserve"}

CONFIDENCE_FIRST = 35
CONFIDENCE_CONFIRMED = 60
CONFIDENCE_STEP = 12
CONFIDENCE_MAX = 95
RELIABLE_THRESHOLD = 60      # une préférence n'influence le matching qu'à partir d'ici


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower().strip())
    return "".join(c for c in s if not unicodedata.combining(c))


def apply_signals(session, user_id: int, signals: list) -> int:
    """Applique une liste de PreferenceSignal (extraits par l'IA) à la mémoire.
    Renvoie le nombre de signaux réellement pris en compte."""
    applied = 0
    for sig in signals:
        dimension = _norm(getattr(sig, "dimension", "") or "")
        orientation = _norm(getattr(sig, "orientation", "") or "")
        key = _norm(getattr(sig, "cle", "") or "")[:80]
        if dimension not in DIMENSIONS or orientation not in ORIENTATIONS or not key:
            continue
        evidence = (getattr(sig, "indice", None) or "")[:300]
        score = getattr(sig, "score", None)

        row = (session.query(Preference)
               .filter(Preference.user_id == user_id,
                       Preference.dimension == dimension,
                       Preference.key == key).first())
        if row is None:
            session.add(Preference(user_id=user_id, dimension=dimension, key=key,
                                   orientation=orientation, score=score,
                                   occurrences=1, confidence=CONFIDENCE_FIRST,
                                   last_evidence=evidence))
        elif row.orientation == orientation:
            row.occurrences += 1
            row.confidence = (CONFIDENCE_CONFIRMED if row.occurrences == 2
                              else min(row.confidence + CONFIDENCE_STEP, CONFIDENCE_MAX))
            if score is not None:
                row.score = score
            if evidence:
                row.last_evidence = evidence
        else:
            # Signal contradictoire : on doute (§10), on ne bascule qu'à répétition
            row.confidence = max(row.confidence - 25, CONFIDENCE_FIRST)
            row.occurrences = 1
            row.orientation = orientation
            if evidence:
                row.last_evidence = evidence
        applied += 1
    session.flush()
    return applied


def summary_for_prompt(session, user_id: int) -> str:
    """Résumé de la mémoire structurée injecté dans le prompt système (§9)."""
    rows = (session.query(Preference).filter(Preference.user_id == user_id)
            .order_by(Preference.confidence.desc()).limit(30).all())
    if not rows:
        return "Aucune préférence apprise pour le moment."
    lines = []
    for r in rows:
        level = ("confirmée" if r.confidence >= 80 else
                 "renforcée" if r.confidence >= RELIABLE_THRESHOLD else "hypothèse faible")
        score = f" {r.score}/10" if r.score is not None else ""
        lines.append(f"- [{r.dimension}] {r.key}{score} : {r.orientation} "
                     f"({level}, {r.occurrences} obs., confiance {r.confidence}%)")
    return "\n".join(lines)


def reliable_preferences(session, user_id: int) -> list[Preference]:
    """Préférences suffisamment confirmées pour influencer le matching (§10-11)."""
    return (session.query(Preference)
            .filter(Preference.user_id == user_id,
                    Preference.confidence >= RELIABLE_THRESHOLD).all())


def matching_adjustment(session, user_id: int, other_profile) -> tuple[float, list[str]]:
    """Ajustement du score de matching (±10 max) selon les préférences confirmées
    de user_id face au profil `other_profile`. Renvoie (points, justifications)."""
    prefs = reliable_preferences(session, user_id)
    if not prefs:
        return 0.0, []

    haystack = _norm(" ".join(filter(None, [
        " ".join(other_profile.personality_traits or []),
        " ".join(other_profile.interests or []),
        " ".join(other_profile.lifestyle_facts or []),
        other_profile.religious_practice or "",
        other_profile.profession or "",
        other_profile.marriage_timeline or "",
    ])))

    total, reasons = 0.0, []
    for p in prefs:
        # correspondance mot-clé : au moins un mot significatif de la clé présent
        words = [w for w in p.key.split() if len(w) >= 4]
        hit = any(w in haystack for w in words)
        if not hit:
            continue
        if p.orientation == "favorable":
            total += 2.5
            reasons.append(f"+ {p.key} (favorable confirmé)")
        elif p.orientation == "defavorable":
            total -= 3.5
            reasons.append(f"- {p.key} (défavorable confirmé)")
        else:  # réserve
            total -= 1.5
            reasons.append(f"~ {p.key} (réserve)")
    total = max(min(total, 10.0), -10.0)
    return round(total, 1), reasons[:6]
