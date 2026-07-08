"""Couche IA : conversation naturelle + extraction structurée du profil.

Un seul appel à l'API Claude par tour de conversation renvoie à la fois la
réponse à envoyer, les informations de profil apprises et le sujet de la
question posée (pour ne jamais se répéter)."""
from __future__ import annotations

import datetime as dt
import json
import logging

from . import config, llm, rag, scripted
from .db import AskedQuestion, Message, Profile, User
from .profile_schema import (BotTurn, CATEGORY_LABELS, FIELD_LABELS,
                             missing_fields)

log = logging.getLogger(__name__)


def ai_enabled() -> bool:
    """Vrai si un moteur IA (Claude ou Ollama/Qwen3) est actif ; sinon mode guidé."""
    return llm.enabled()


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


def build_system_prompt(profile: Profile, asked_topics: list[str],
                        preferences_summary: str = "",
                        match_context: str = "") -> str:
    missing = missing_fields(profile)
    next_targets = [FIELD_LABELS.get(f, f) for f in missing[:3]]
    snapshot = json.dumps(profile_snapshot(profile), ensure_ascii=False, indent=2)
    asked = ", ".join(asked_topics) if asked_topics else "aucune"

    return f"""Tu es l'assistant IA d'une communauté Telegram de rencontre sérieuse entre musulmans et musulmanes en vue du mariage. Tu fonctionnes comme un conseiller de mise en relation expérimenté. Tu discutes en privé, en français, avec un membre.

TON RÔLE (charte du projet)
- Ton rôle EST : observer, comprendre, analyser, structurer les informations, améliorer progressivement la qualité des suggestions.
- Ton rôle N'EST PAS : convaincre, vendre un profil, pousser deux personnes à se rencontrer, juger.
- Tu ne manipules jamais, tu n'exagères jamais une compatibilité, tu ne caches pas une information importante, tu ne fais pas de diagnostic psychologique, et tu ne présentes JAMAIS une supposition comme une certitude.
- Tu es respectueux, neutre, bienveillant, et tu respectes les convictions religieuses.

PHILOSOPHIE : PAS DE FORMULAIRE
- L'utilisateur ne doit jamais avoir l'impression de remplir un questionnaire.
- Les informations les plus précieuses viennent de ses RÉACTIONS : commentaires sur les profils proposés, remarques positives ou négatives, hésitations, priorités exprimées naturellement. Une personne révèle mieux ses préférences en analysant un exemple concret qu'en répondant à une question abstraite.
- Quand un profil vient de lui être proposé (voir CONTEXTE plus bas), recueille son ressenti et analyse-le en profondeur plutôt que de poser des questions de profil.
- Ne redemande JAMAIS une information déjà connue (profil ci-dessous, sujets déjà abordés : {asked}).
- UNE seule question par message maximum ; parfois aucune, juste un échange naturel.
- Rebondis sur les réponses pour approfondir ; fais référence aux éléments mémorisés pour montrer que tu te souviens.
- Réponds d'abord à ce que dit la personne (question, émotion), puis enchaîne naturellement.
- Si la personne ne veut pas répondre, respecte-le et passe à autre chose.
- Pas de conseil médical, juridique, ni de fatwa. Ne révèle jamais l'identité d'autres membres.

ANALYSE DES RÉACTIONS (dimensions à observer)
A. Valeurs : famille, spiritualité, stabilité, ambition, simplicité, générosité, transmission.
B. Vision du couple : attentes envers le conjoint, partage des responsabilités, communication, gestion des conflits, place des familles.
C. Personnalité relationnelle : besoin de communication, sociabilité, indépendance, expression des émotions, gestion des désaccords.
D. Mode de vie : rythme quotidien, loisirs, travail, sorties, environnement familial.
Chaque réaction significative produit des `preference_signals`. Jamais de conclusion définitive sur une seule réaction : le système renforce les hypothèses par répétition.

COLLECTE PROGRESSIVE (en complément des réactions)
Champs encore inconnus, à découvrir en douceur quand la conversation s'y prête : {", ".join(next_targets) if next_targets else "profil très complet — privilégie l'analyse des réactions et l'approfondissement"}.
Ordre général : {", ".join(CATEGORY_LABELS.values())}.

PROFIL ACTUEL (indice de connaissance : {profile.completeness}/100)
{snapshot}

MÉMOIRE STRUCTURÉE DES PRÉFÉRENCES (apprise des réactions)
{preferences_summary or "Aucune préférence apprise pour le moment."}
{match_context}
SORTIE STRUCTURÉE
- `reply` : ton message (2 à 4 phrases maximum).
- `updates` : uniquement les faits réellement communiqués dans le dernier message (ne devine rien).
- `asked_topic` : clé du champ visé par ta question, ou null.
- `memory_notes` : faits marquants à retenir (max 2).
- `preference_signals` : signaux détectés dans la réaction (dimension, clé courte réutilisable, orientation favorable/defavorable/reserve, score 0-10 pour les valeurs, indice = courte citation). N'en émets que si le message en contient réellement.

Date du jour : {dt.date.today().isoformat()}."""


def converse(profile: Profile, history: list[dict], asked_topics: list[str],
             preferences_summary: str = "", match_context: str = "",
             rag_context: str = "") -> BotTurn:
    """Appelle le moteur IA actif (Claude ou Qwen3) et renvoie la réponse structurée."""
    system = build_system_prompt(profile, asked_topics, preferences_summary,
                                 match_context + rag_context)
    return llm.chat_structured(system, history, BotTurn)


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

    # RAG actif (Ollama) : fenêtre d'historique COURTE + souvenirs pertinents
    # récupérés de la mémoire vectorielle. Sinon : fenêtre d'historique large.
    use_rag = llm.rag_enabled()
    window = 6 if use_rag else config.CONVERSATION_WINDOW
    rows = (session.query(Message)
            .filter(Message.user_id == user.telegram_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(window).all())
    history = [{"role": m.role, "content": m.content} for m in reversed(rows)]
    while history and history[0]["role"] != "user":  # commencer par un tour user
        history.pop(0)

    asked_topics = [q.topic for q in session.query(AskedQuestion)
                    .filter(AskedQuestion.user_id == user.telegram_id).all()]

    from . import preferences as prefs
    pref_summary = prefs.summary_for_prompt(session, user.telegram_id)
    match_context = _recent_match_context(session, user.telegram_id)
    rag_context = rag.context_block(session, user.telegram_id, text) if use_rag else ""

    turn = converse(profile, history, asked_topics, pref_summary,
                    match_context, rag_context)
    apply_updates(profile, turn)
    prefs.apply_signals(session, user.telegram_id, turn.preference_signals)

    if turn.asked_topic and turn.asked_topic not in asked_topics:
        session.add(AskedQuestion(user_id=user.telegram_id, topic=turn.asked_topic))

    session.add(Message(user_id=user.telegram_id, role="assistant", content=turn.reply))

    # Indexation dans la mémoire vectorielle (déport du contexte)
    if use_rag:
        rag.index_text(session, user.telegram_id, "echange", f"Il a dit : {text}")
        for note in turn.memory_notes:
            rag.index_text(session, user.telegram_id, "fait", note)
        for sig in turn.preference_signals:
            if sig.indice:
                rag.index_text(session, user.telegram_id, "preference",
                               f"{sig.cle} ({sig.orientation}) : {sig.indice}")

    return turn.reply


def _recent_match_context(session, user_id: int) -> str:
    """Contexte du dernier profil proposé (pour interpréter les réactions, §7)."""
    import datetime as _dt

    from .db import Match, utcnow
    cutoff = utcnow() - _dt.timedelta(days=7)
    match = (session.query(Match)
             .filter(((Match.user_m_id == user_id) | (Match.user_f_id == user_id)),
                     Match.updated_at >= cutoff)
             .order_by(Match.updated_at.desc()).first())
    if match is None:
        return ""
    other_id = match.user_f_id if match.user_m_id == user_id else match.user_m_id
    other = session.get(Profile, other_id)
    if other is None:
        return ""
    response = match.response_m if match.user_m_id == user_id else match.response_f
    labels = {"pending": "pas encore répondu", "accepted": "accepté", "refused": "refusé",
              "postponed": "reporté", "info": "a demandé plus d'informations"}
    return (f"\nCONTEXTE — DERNIER PROFIL PROPOSÉ À CE MEMBRE (réaction : {labels.get(response, response)})\n"
            f"Profil anonyme : {other.gender}, {other.age} ans, {other.city or '?'} "
            f"({other.country or '?'}), {other.profession or '?'} ; "
            f"personnalité : {', '.join((other.personality_traits or [])[:4]) or '?'} ; "
            f"intérêts : {', '.join((other.interests or [])[:4]) or '?'} ; "
            f"pratique : {other.religious_practice or '?'}.\n"
            f"Si le membre commente ce profil, analyse sa réaction en priorité "
            f"(preference_signals) et recueille son ressenti.\n")


def generate_profile_presentation(other: Profile) -> str | None:
    """Présentation narrative et anonymisée d'un profil (charte §6) : humaine,
    réaliste, suffisamment détaillée pour provoquer une réaction — pas une liste
    de caractéristiques techniques. Renvoie None si l'IA est indisponible."""
    if not ai_enabled():
        return None
    facts = json.dumps({
        "sexe": other.gender, "age": other.age, "ville": other.city,
        "pays": other.country, "profession": other.profession,
        "etudes": other.education, "situation": other.marital_status,
        "delai_mariage": other.marriage_timeline,
        "souhaite_enfants": other.wants_children,
        "pratique_religieuse": other.religious_practice,
        "personnalite": (other.personality_traits or [])[:5],
        "centres_interet": (other.interests or [])[:5],
        "habitudes": (other.lifestyle_facts or [])[:4],
    }, ensure_ascii=False)
    try:
        text = llm.chat_text(
            "Rédige la présentation anonymisée d'un profil pour une plateforme de "
            "rencontre musulmane sérieuse, à partir de ces informations factuelles :\n"
            f"{facts}\n\n"
            "Règles : en français, 3 à 5 phrases chaleureuses et humaines ; commence par "
            "« Ce frère » ou « Cette sœur » selon le sexe ; raconte la personne (valeurs, "
            "façon d'être, ce qui compte pour elle) plutôt que d'énumérer des critères ; "
            "n'invente RIEN qui ne soit pas dans les informations fournies ; ne révèle ni "
            "prénom ni élément identifiant ; n'exagère pas la compatibilité. "
            "Réponds uniquement par la présentation, sans préambule.").strip()
        return text or None
    except Exception:
        log.exception("Présentation narrative indisponible, repli sur la fiche standard")
        return None


def generate_community_text(kind: str, context: str = "") -> str:
    """Génère un contenu d'animation communautaire (question, quiz, rappel...).
    Sans IA — ou si l'appel échoue — utilise la banque de contenus statiques."""
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
    try:
        return llm.chat_text(prompts.get(kind, prompts["question"]) +
                             (f"\nContexte : {context}" if context else "")).strip()
    except Exception:
        log.exception("Génération communautaire indisponible, repli statique")
        return scripted.static_community_text(kind)
