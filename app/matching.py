"""Moteur de matching : compare les profils homme/femme et calcule un score 0-100.

Trois niveaux, conformément au cahier des charges :
- compatibilités OBLIGATOIRES (filtres éliminatoires) : sexes opposés, objectif
  mariage, tranche d'âge, complétude minimale ;
- compatibilités IMPORTANTES (70 pts) : pratique religieuse, projet de famille,
  localisation, personnalité ;
- compatibilités SECONDAIRES (30 pts) : centres d'intérêt, habitudes de vie.
"""
from __future__ import annotations

import unicodedata

from sqlalchemy import and_, or_

from . import config
from .db import Match, Profile, User

AGE_MAX_GAP = 12          # écart d'âge maximal accepté (filtre obligatoire)


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s.lower().strip())
    return "".join(c for c in s if not unicodedata.combining(c))


def _norm_set(items: list | None) -> set[str]:
    return {_norm(i) for i in (items or []) if i}


def _overlap_score(a: list | None, b: list | None) -> float:
    """Proportion de recouvrement (0-1) entre deux listes de textes."""
    sa, sb = _norm_set(a), _norm_set(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    return inter / min(len(sa), len(sb))


PRACTICE_KEYWORDS = [
    ("assidu", 3), ("5 priere", 3), ("cinq priere", 3), ("pratiquant", 3),
    ("regulier", 2), ("prie", 2), ("apprend", 2),
    ("debut", 1), ("peu", 1), ("occasionnel", 1),
]


def _practice_level(profile: Profile) -> int | None:
    """Niveau de pratique approximatif (1-3) déduit du texte libre."""
    text = _norm(" ".join(filter(None, [profile.religious_practice,
                                        profile.mosque_attendance,
                                        profile.religious_education])))
    if not text:
        return None
    best = None
    for keyword, level in PRACTICE_KEYWORDS:
        if keyword in text:
            best = max(best or 0, level) if level >= (best or 0) else best
    return best if best else 2  # pratique mentionnée sans précision -> moyen


def hard_filters_ok(pm: Profile, pf: Profile) -> bool:
    """Compatibilités obligatoires. pm = profil homme, pf = profil femme."""
    if pm.gender != "homme" or pf.gender != "femme":
        return False
    if (pm.completeness or 0) < config.MIN_COMPLETENESS_FOR_MATCHING:
        return False
    if (pf.completeness or 0) < config.MIN_COMPLETENESS_FOR_MATCHING:
        return False
    age_m, age_f = pm.age, pf.age
    if age_m is None or age_f is None:
        return False
    if age_m < 18 or age_f < 18:
        return False
    if abs(age_m - age_f) > AGE_MAX_GAP:
        return False
    return True


def compatibility(pm: Profile, pf: Profile) -> tuple[float, dict]:
    """Score 0-100 + décomposition. Suppose les filtres obligatoires passés."""
    details: dict[str, float] = {}

    # --- Importantes (70) ---
    # Pratique religieuse (25)
    lm, lf = _practice_level(pm), _practice_level(pf)
    if lm is None or lf is None:
        religion = 12.0                      # inconnu -> neutre
    else:
        religion = 25.0 - abs(lm - lf) * 10  # même niveau: 25, écart max: 5
    details["pratique_religieuse"] = max(religion, 0)

    # Projet de famille (20)
    family = 0.0
    if pm.wants_children is not None and pf.wants_children is not None:
        family += 14 if pm.wants_children == pf.wants_children else 0
    else:
        family += 7
    if pm.children_count_desired and pf.children_count_desired:
        family += max(6 - abs(pm.children_count_desired - pf.children_count_desired) * 2, 0)
    else:
        family += 3
    details["projet_famille"] = family

    # Localisation (15)
    if _norm(pm.city) and _norm(pm.city) == _norm(pf.city):
        loc = 15.0
    elif _norm(pm.department) and _norm(pm.department) == _norm(pf.department):
        loc = 12.0
    elif _norm(pm.country) and _norm(pm.country) == _norm(pf.country):
        loc = 8.0
    elif not pm.country or not pf.country:
        loc = 4.0
    else:
        loc = 0.0
    details["localisation"] = loc

    # Personnalité (10) — recouvrement des traits déclarés
    details["personnalite"] = round(_overlap_score(pm.personality_traits,
                                                   pf.personality_traits) * 10, 1)

    # Écart d'âge (bonus dans la partie importante, déjà filtré) — intégré à
    # la localisation/personnalité ? Non : petit ajustement via secondaires.

    # --- Secondaires (30) ---
    details["centres_interet"] = round(_overlap_score(pm.interests, pf.interests) * 18, 1)
    details["habitudes_vie"] = round(_overlap_score(pm.lifestyle_facts, pf.lifestyle_facts) * 7, 1)
    age_gap = abs((pm.age or 0) - (pf.age or 0))
    details["proximite_age"] = round(max(5 - age_gap * 0.8, 0), 1)

    score = round(min(sum(details.values()), 100), 1)
    return score, details


def find_new_matches(session) -> list[Match]:
    """Calcule les paires compatibles non encore proposées et crée les Match
    dont le score dépasse le seuil."""
    profiles = (session.query(Profile).join(User)
                .filter(User.is_active.is_(True)).all())
    men = [p for p in profiles if p.gender == "homme"]
    women = [p for p in profiles if p.gender == "femme"]

    existing = {(m.user_m_id, m.user_f_id) for m in session.query(Match).all()}
    # Exclut les paires ayant fait l'objet d'un signalement (modération)
    from .db import Report
    blocked: set[tuple[int, int]] = set()
    for r in session.query(Report).filter(Report.reported_id.isnot(None)).all():
        blocked.add((r.reporter_id, r.reported_id))
        blocked.add((r.reported_id, r.reporter_id))
    created: list[Match] = []
    for pm in men:
        for pf in women:
            if (pm.user_id, pf.user_id) in existing:
                continue
            if (pm.user_id, pf.user_id) in blocked:
                continue
            if not hard_filters_ok(pm, pf):
                continue
            score, details = compatibility(pm, pf)

            # Préférences déduites des réactions (charte §11) : les préférences
            # confirmées de chacun ajustent le score face au profil de l'autre.
            from . import preferences as prefs
            adj_m, reasons_m = prefs.matching_adjustment(session, pm.user_id, pf)
            adj_f, reasons_f = prefs.matching_adjustment(session, pf.user_id, pm)
            if adj_m or adj_f:
                details["preferences_deduites"] = round(adj_m + adj_f, 1)
                details["preferences_detail"] = {"homme": reasons_m, "femme": reasons_f}
                score = round(max(min(score + adj_m + adj_f, 100), 0), 1)

            if score >= config.MATCH_THRESHOLD:
                match = Match(user_m_id=pm.user_id, user_f_id=pf.user_id,
                              score=score, details=details)
                session.add(match)
                created.append(match)
    session.flush()
    return created


def register_response(session, match: Match, responder_id: int, response: str) -> Match:
    """Enregistre la réponse d'un membre (accepted / refused / postponed / info)
    et met à jour le statut global."""
    if responder_id == match.user_m_id:
        match.response_m = response
    elif responder_id == match.user_f_id:
        match.response_f = response

    if "refused" in (match.response_m, match.response_f):
        match.status = "refused"
    elif match.response_m == "accepted" and match.response_f == "accepted":
        match.status = "mutual"
    else:
        match.status = "proposed"
    session.flush()
    return match
