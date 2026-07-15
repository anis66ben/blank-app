"""RGPD : consentement, export et suppression des données personnelles.

Obligations couvertes : information + consentement (art. 6/7), droit d'accès
(art. 15) via /mesdonnees, droit à l'effacement (art. 17) via /supprimer.
"""
from __future__ import annotations

import datetime as dt
import json

from .db import (AskedQuestion, Match, MemoryChunk, Message, Preference,
                 Profile, User)

CONSENT_TEXT = (
    "🔒 *Protection de tes données*\n\n"
    "Pour te proposer des profils compatibles, ce service enregistre les "
    "informations que tu partages (profil, préférences) et l'historique de nos "
    "échanges. Ces données servent uniquement à la mise en relation au sein de "
    "cette communauté. Elles ne sont ni vendues, ni cédées à des tiers.\n\n"
    "En cas de match mutuel accepté par les deux personnes, ton identifiant "
    "Telegram est partagé avec l'autre membre pour vous permettre de vous "
    "contacter.\n\n"
    "Tu gardes le contrôle à tout moment :\n"
    "• /mesdonnees — voir les données te concernant\n"
    "• /supprimer — effacer définitivement ton profil et tes échanges\n"
    "• /pause — suspendre les suggestions\n\n"
    "En appuyant sur « J'accepte », tu confirmes avoir plus de 18 ans et "
    "consentir à ce traitement."
)


def count_messages_today(session, user_id: int) -> int:
    """Nombre de messages envoyés par le membre depuis minuit UTC (plafond coût)."""
    start = dt.datetime.now(dt.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    return (session.query(Message)
            .filter(Message.user_id == user_id, Message.role == "user",
                    Message.created_at >= start).count())


def export_data(session, user_id: int) -> str:
    """Résumé lisible des données du membre (droit d'accès)."""
    user = session.get(User, user_id)
    if user is None:
        return "Aucune donnée enregistrée à ton sujet."
    p = user.profile
    n_msg = session.query(Message).filter(Message.user_id == user_id).count()
    prefs = session.query(Preference).filter(Preference.user_id == user_id).all()
    data = {
        "identifiant_telegram": user.telegram_id,
        "pseudo_telegram": user.username,
        "inscription": user.created_at.isoformat(),
        "consentement": user.consented_at.isoformat() if user.consented_at else None,
        "profil": {
            "prenom": p.pseudo, "sexe": p.gender, "age": p.age,
            "ville": p.city, "pays": p.country, "profession": p.profession,
            "situation": p.marital_status,
            "personnalite": p.personality_traits or [],
            "centres_interet": p.interests or [],
            "completude": p.completeness,
        },
        "preferences_apprises": [f"{pr.key} ({pr.orientation})" for pr in prefs],
        "nombre_de_messages": n_msg,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def delete_data(session, user_id: int) -> bool:
    """Efface définitivement toutes les données du membre (droit à l'effacement)."""
    if session.get(User, user_id) is None:
        return False
    for model in (MemoryChunk, Preference, AskedQuestion, Message):
        session.query(model).filter(model.user_id == user_id).delete()
    session.query(Match).filter(
        (Match.user_m_id == user_id) | (Match.user_f_id == user_id)).delete()
    session.query(Profile).filter(Profile.user_id == user_id).delete()
    session.query(User).filter(User.telegram_id == user_id).delete()
    return True
