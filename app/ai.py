"""Couche IA : conversation naturelle + extraction structurée du profil.

Un seul appel à l'API Claude par tour de conversation renvoie à la fois la
réponse à envoyer, les informations de profil apprises et le sujet de la
question posée (pour ne jamais se répéter)."""
from __future__ import annotations

import datetime as dt
import json
import logging

import anthropic

from . import config, scripted
from .db import AskedQuestion, Message, Profile, User
from .profile_schema import (BotTurn, CATEGORY_LABELS, FIELD_LABELS,
                             missing_fields)

log = logging.getLogger(__name__)


def ai_enabled() -> bool:
    """L'IA est active si une clé API est configurée ; sinon, mode guidé."""
    return bool(config.ANTHROPIC_API_KEY)

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY or None)
    return _client


def profile_snapshot(profile: Profile) -> dict:
    """Représentation JSON du profil pour le prompt système."""
    return {
        "pseudo": profile.pseudo,
        "sexe": profile.gender,
        "date_naissance": profile.birth_date.isoformat() if profile.birth_date else None,
        "age": profile.age,
        "lieu_naissance": profile.birth_place,
        "ville": profile.city,
        "departement": profile.department,
        "pays": profile.country,
        "profession": profile.profession,
        "etudes": profile.education,
        "situation": profile.marital_status,
        "delai_mariage": profile.marriage_timeline,
        "souhaite_enfants": profile.wants_children,
        "nombre_enfants_souhaite": profile.children_count_desired,
        "pratique_religieuse": profile.religious_practice,
        "mosquee": profile.mosque_attendance,
        "apprentissage_religieux": profile.religious_education,
        "personnalite": profile.personality_traits or [],
        "centres_interet": profile.interests or [],
        "habitudes_vie": profile.lifestyle_facts or [],
        "notes_memorisees": profile.memory_notes or [],
        "indice_connaissance": profile.completeness,
    }


def build_system_prompt(profile: Profile, asked_topics: list[str]) -> str:
    missing = missing_fields(profile)
    next_targets = [FIELD_LABELS.get(f, f) for f in missing[:3]]
    snapshot = json.dumps(profile_snapshot(profile), ensure_ascii=False, indent=2)
    asked = ", ".join(asked_topics) if asked_topics else "aucune"

    return f"""Tu es l'assistant d'une plateforme de rencontre sérieuse entre musulmans et musulmanes en vue du mariage. Tu discutes en privé, en français, avec un membre pour apprendre à le connaître progressivement.

RÈGLES DE CONVERSATION
- Ton chaleureux, respectueux et naturel, conforme à l'éthique musulmane (pas de familiarité déplacée).
- UNE seule question par message, jamais plus. La conversation doit rester légère, pas un interrogatoire.
- Ne repose JAMAIS une question déjà posée (sujets déjà abordés : {asked}). Si l'information est déjà dans le profil, ne la redemande pas.
- Rebondis sur les réponses pour approfondir (ex. s'il aime voyager, demande quel type de voyage, puis quel pays l'a marqué).
- Fais parfois référence à des éléments mémorisés lors d'échanges précédents pour montrer que tu te souviens.
- Réponds d'abord à ce que dit la personne (question, émotion, remarque), puis enchaîne naturellement.
- Si la personne ne veut pas répondre à une question, respecte-le et passe à autre chose.
- Ne donne jamais de conseil médical, juridique ou de fatwa ; reste sur ton rôle de mise en relation.
- Ne communique jamais l'identité d'autres membres dans cette conversation.

COLLECTE PROGRESSIVE
Le profil s'enrichit au fil des jours : d'abord l'identité générale, puis la situation personnelle, le projet de mariage et de famille, la pratique religieuse, la personnalité, et enfin les centres d'intérêt et habitudes de vie ({", ".join(CATEGORY_LABELS.values())}).
Prochaines informations à découvrir en priorité : {", ".join(next_targets) if next_targets else "le profil est très complet — approfondis la personnalité et les projets"}.

PROFIL ACTUEL (indice de connaissance : {profile.completeness}/100)
{snapshot}

SORTIE STRUCTURÉE
- `reply` : ton message (2 à 4 phrases maximum).
- `updates` : uniquement les faits réellement communiqués par la personne dans son dernier message (ne devine rien).
- `asked_topic` : la clé du champ de profil visé par ta question (ex. "profession"), ou null si tu n'as pas posé de question.
- `memory_notes` : faits marquants à retenir pour les prochaines conversations (max 2).

Date du jour : {dt.date.today().isoformat()}."""


def converse(profile: Profile, history: list[dict], asked_topics: list[str]) -> BotTurn:
    """Appelle Claude et renvoie la réponse structurée du tour."""
    client = get_client()
    system = build_system_prompt(profile, asked_topics)
    response = client.messages.parse(
        model=config.CLAUDE_MODEL,
        max_tokens=2048,
        system=[{"type": "text", "text": system}],
        messages=history,
        output_format=BotTurn,
    )
    turn = response.parsed_output
    if turn is None:  # sécurité : réponse non conforme
        raise RuntimeError("Réponse du modèle non structurée")
    return turn


def apply_updates(profile: Profile, turn: BotTurn) -> None:
    """Applique les informations extraites au profil (sans écraser par du vide)."""
    u = turn.updates
    scalar_fields = ["pseudo", "gender", "birth_place", "city", "department", "country",
                     "profession", "education", "marital_status", "marriage_timeline",
                     "wants_children", "children_count_desired", "religious_practice",
                     "mosque_attendance", "religious_education", "age_estimate"]
    for field in scalar_fields:
        value = getattr(u, field, None)
        if value is not None and str(value).strip() != "":
            setattr(profile, field, value)

    if u.birth_date:
        try:
            profile.birth_date = dt.date.fromisoformat(u.birth_date.strip())
        except ValueError:
            log.warning("Date de naissance invalide ignorée : %r", u.birth_date)

    for list_field, new_items in [("personality_traits", u.personality_traits),
                                  ("interests", u.interests),
                                  ("lifestyle_facts", u.lifestyle_facts),
                                  ("memory_notes", turn.memory_notes)]:
        if new_items:
            current = list(getattr(profile, list_field) or [])
            lowered = {i.lower() for i in current}
            for item in new_items:
                if item and item.lower() not in lowered:
                    current.append(item)
                    lowered.add(item.lower())
            setattr(profile, list_field, current[-40:])  # borne la taille

    profile.refresh_completeness()


def handle_user_message(session, user: User, text: str) -> str:
    """Tour complet : enregistre le message, appelle l'IA, met à jour le profil,
    enregistre la réponse. Renvoie le texte à envoyer.

    Sans clé API (ANTHROPIC_API_KEY vide), bascule sur le questionnaire guidé."""
    if not ai_enabled():
        return scripted.handle_user_message(session, user, text)

    profile = user.profile
    session.add(Message(user_id=user.telegram_id, role="user", content=text))
    session.flush()

    rows = (session.query(Message)
            .filter(Message.user_id == user.telegram_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(config.CONVERSATION_WINDOW).all())
    history = [{"role": m.role, "content": m.content} for m in reversed(rows)]
    # L'API exige que la conversation commence par un tour utilisateur
    while history and history[0]["role"] != "user":
        history.pop(0)

    asked_topics = [q.topic for q in session.query(AskedQuestion)
                    .filter(AskedQuestion.user_id == user.telegram_id).all()]

    turn = converse(profile, history, asked_topics)
    apply_updates(profile, turn)

    if turn.asked_topic and turn.asked_topic not in asked_topics:
        session.add(AskedQuestion(user_id=user.telegram_id, topic=turn.asked_topic))

    session.add(Message(user_id=user.telegram_id, role="assistant", content=turn.reply))
    return turn.reply


def generate_community_text(kind: str, context: str = "") -> str:
    """Génère un contenu d'animation communautaire (question, quiz, rappel...).
    Sans clé API — ou si l'appel échoue — utilise la banque de contenus statiques."""
    if not ai_enabled():
        return scripted.static_community_text(kind)
    prompts = {
        "question": "Rédige une unique question de réflexion bienveillante pour un groupe Telegram "
                    "de musulmans célibataires cherchant le mariage (thèmes : vie de couple, valeurs, "
                    "famille, spiritualité). Une ou deux phrases, engageante, sans préambule.",
        "quiz": "Rédige un mini-quiz de culture islamique pour un groupe Telegram : une question et "
                "quatre propositions A/B/C/D, puis la bonne réponse sur une ligne 'Réponse : X'. "
                "Ton léger et accessible, sans préambule.",
        "rappel_regles": "Rédige un rappel court et bienveillant des règles d'un groupe Telegram de "
                         "rencontre entre musulmans : respect, pudeur dans les échanges, pas de contact "
                         "privé non sollicité, signaler les abus. 4 à 5 lignes avec des puces, sans préambule.",
    }
    client = get_client()
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompts.get(kind, prompts["question"]) +
                   (f"\nContexte : {context}" if context else "")}],
    )
    return next((b.text for b in response.content if b.type == "text"), "").strip()
