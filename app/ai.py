"""Couche IA : conversation naturelle + extraction structurée du profil.

Un seul appel à l'API Claude par tour de conversation renvoie à la fois la
réponse à envoyer, les informations de profil apprises et le sujet de la
question posée (pour ne jamais se répéter)."""
from __future__ import annotations

import datetime as dt
import json
import logging

from . import config, convlog, llm, rag, scripted
from .db import AskedQuestion, Message, Profile, User
from .persona import PERSONA_BRIEF, PERSONA_PROMPT
from .profile_schema import (BotTurn, CATEGORY_LABELS, COMPLETENESS_WEIGHTS,
                             Extraction, FIELD_LABELS, LIST_FIELD_TARGETS,
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
        "recherche_conjoint": {
            "age_min": profile.sought_age_min, "age_max": profile.sought_age_max,
            "localisation": profile.sought_location, "pratique": profile.sought_religious,
            "veut_enfants": profile.sought_wants_children,
            "qualites": profile.sought_qualities or [],
        },
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

    return f"""{PERSONA_PROMPT}

---
CADRE OPÉRATIONNEL (à respecter en plus des principes ci-dessus)

- Tu es l'ASSISTANT, pas un membre : tu n'as ni âge, ni ville, ni goûts, ni biographie, et tu n'en inventes jamais. Ne parle pas de toi ; si on te pose une question personnelle, dis simplement que tu es là pour la personne et recentre sur elle.
- Ne redemande JAMAIS une information déjà connue (profil ci-dessous ; sujets déjà abordés : {asked}).
- Une seule piste/question par message, parfois aucune. Réponds d'abord à ce que dit la personne, puis ouvre une porte.
- Quand un profil vient d'être proposé au membre (voir CONTEXTE plus bas), analyse sa réaction en priorité et recueille son ressenti.
- Ne présente jamais une supposition comme une certitude ; formule des hypothèses. Pas de conseil médical/juridique ni de fatwa. Ne révèle jamais l'identité d'autres membres.

PROFIL ACTUEL DÉJÀ CONNU (indice de connaissance : {profile.completeness}/100)
{snapshot}
Informations encore inconnues à découvrir naturellement quand la conversation s'y prête : {", ".join(next_targets) if next_targets else "profil déjà riche — approfondis les valeurs, la vision de vie et les aspirations"}.

MÉMOIRE STRUCTURÉE DES PRÉFÉRENCES (déjà apprise)
{preferences_summary or "Aucune préférence apprise pour le moment."}
{match_context}
FORMAT DE SORTIE (JSON structuré — indispensable au fonctionnement de l'application)
- `reply` : ton message à la personne (chaleureux, 2 à 4 phrases, une seule porte ouverte à la fin).
- `updates` : uniquement les faits factuels réellement communiqués dans le dernier message (prénom, âge, ville, profession, situation… ; ne devine rien, laisse null sinon).
- `asked_topic` : clé du champ de profil visé par ta question, ou null.
- `memory_notes` : 1 à 2 faits marquants du portrait à retenir (valeur, aspiration, expérience clé).
- `preference_signals` : hypothèses détectées (dimension = valeurs/vision_couple/personnalite/mode_de_vie/preference_profil ; cle courte réutilisable ; orientation favorable/defavorable/reserve ; score 0-10 pour les valeurs ; indice = courte citation). N'en émets QUE si le message en contient réellement.

Date du jour : {dt.date.today().isoformat()}."""


def build_reply_prompt(profile: Profile, asked_topics: list[str],
                       preferences_summary: str = "", extra_context: str = "") -> str:
    """Prompt pour la RÉPONSE conversationnelle seule (texte, sans JSON).
    Le profil connu est un CONTEXTE PRIVÉ (pour ne pas reposer une question),
    jamais à réciter — sinon le petit modèle énonce les traits du profil et part
    hors sujet."""
    missing = missing_fields(profile)
    next_targets = [FIELD_LABELS.get(f, f) for f in missing[:3]]
    known = [FIELD_LABELS.get(f, f) for f in COMPLETENESS_WEIGHTS
             if f not in LIST_FIELD_TARGETS and getattr(profile, f, None)]
    if profile.age:
        known.append("âge")
    asked = ", ".join(asked_topics) if asked_topics else "aucune"
    return f"""{PERSONA_BRIEF}

---
CONTEXTE PRIVÉ (pour toi seul — NE le récite JAMAIS à la personne, ne lui décris pas son propre caractère ni ses goûts) :
- Prénom : {profile.pseudo or "inconnu"}
- Déjà connu, donc à NE PAS redemander : {", ".join(known) if known else "rien encore"}
- Questions déjà posées : {asked}
- Préférences déjà comprises : {preferences_summary or "aucune"}
- À découvrir plus tard, en douceur : {", ".join(next_targets) if next_targets else "ses valeurs, sa vision de la vie, ses aspirations"}
{extra_context}
RÈGLES POUR TA RÉPONSE — IMPÉRATIF ABSOLU :
1. Tu es l'ASSISTANT, pas un membre. Ne parle JAMAIS de toi : n'invente ni âge, ni ville, ni pays, ni goûts, ni histoire pour toi-même. Interdit de dire « je suis né… », « j'aime… », « moi aussi ». Si on te pose une question perso, dis en une phrase que tu es là pour elle et recentre sur elle.
2. Réponds AVANT TOUT à ce que la personne vient d'écrire, sur SON sujet. Ne parle pas de son profil, ne lui énumère pas ses traits, ne récite jamais ce que tu sais déjà.
3. Adapte-toi à son registre. Salutation ou banalité (« salam », « ça va », « ok ») → réponse simple et chaleureuse, au plus une petite question légère ; n'ouvre PAS de grand sujet.
4. Ne commence PAS en répétant ses mots. Réagis naturellement.
5. Au plus UNE question, courte, qui prolonge NATURELLEMENT ce qu'elle vient de dire — jamais plaquée ni recopiée de ce prompt.
6. Ne repose jamais une question déjà posée ; ne répète jamais une formule déjà employée.
7. Bref et humain : 1 à 3 phrases. Pas de préambule, pas de guillemets.

Écris uniquement ton message, en français."""


EXTRACT_PROMPT = """Tu es un extracteur d'informations pour un profil de rencontre. À partir UNIQUEMENT du message du membre ci-dessous, renseigne les champs qu'il a EXPLICITEMENT écrits DANS CE MESSAGE.

RÈGLES ABSOLUES :
- N'extrais QUE ce que la personne dit SUR ELLE-MÊME. Si elle parle du bot, d'une autre personne, ou pose une question (« toi tu es né où ? », « tu aimes ça ? »), n'extrais RIEN.
- N'invente RIEN. Ne recopie RIEN qui ne soit pas dans ce message précis.
- Si le message est une salutation ou une banalité (« Salam », « oui », « ok », « merci », « ça va »), renvoie TOUT vide.
- `updates` = seulement les faits que la personne dit sur elle maintenant (son prénom, son âge, sa ville, etc.).
- `preference_signals` = seulement si la personne exprime SON goût / SA valeur / SA réserve.

Exemples :
Message : « Salam »  →  {"updates": {}, "asked_topic": null, "memory_notes": [], "preference_signals": []}
Message : « Toi t'es né à Alger ?! »  →  {"updates": {}, "asked_topic": null, "memory_notes": [], "preference_signals": []}  (elle parle du bot, pas d'elle → rien)
Message : « oui dis moi »  →  {"updates": {}, "asked_topic": null, "memory_notes": [], "preference_signals": []}
Message : « Moi je m'appelle Sami, j'ai 28 ans et je vis à Lyon »  →  {"updates": {"pseudo": "Sami", "age_estimate": 28, "city": "Lyon"}, "asked_topic": null, "memory_notes": [], "preference_signals": []}
Message : « J'aimerais une femme proche de sa famille »  →  {"updates": {}, "asked_topic": null, "memory_notes": ["Attache de l'importance à la proximité familiale"], "preference_signals": [{"dimension": "valeurs", "cle": "famille", "orientation": "favorable", "score": 7, "indice": "proche de sa famille"}]}"""


_TRIVIAL = {"salam", "salut", "bonjour", "bonsoir", "coucou", "hello", "hey",
            "ok", "oui", "non", "merci", "ca", "va", "cava", "bien", "yo",
            "wa", "alaykoum", "aleykoum", "assalamou", "slt", "cc", "dacc", "daccord"}


def _is_trivial(message: str) -> bool:
    """Message sans information à extraire (salutation, acquiescement) : on saute
    l'appel d'extraction pour gagner du temps."""
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", message.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    words = re.findall(r"[a-z0-9']{2,}", s)
    if not words:
        return True
    return len(words) <= 4 and all(w in _TRIVIAL for w in words)


def _extract(last_user_message: str) -> Extraction:
    """Extraction bornée au seul dernier message (empêche la recopie du profil)."""
    if not last_user_message.strip() or _is_trivial(last_user_message):
        return Extraction()
    try:
        return llm.chat_structured(EXTRACT_PROMPT,
                                   [{"role": "user", "content": last_user_message}],
                                   Extraction)
    except Exception:
        log.warning("Extraction échouée, ignorée", exc_info=False)
        return Extraction()


def converse(profile: Profile, history: list[dict], asked_topics: list[str],
             preferences_summary: str = "", match_context: str = "",
             rag_context: str = "", meta: dict | None = None) -> BotTurn:
    """Appelle le moteur IA actif et renvoie la réponse structurée.

    - Claude (modèle puissant) : un seul appel structuré (réponse + extraction).
    - Petit modèle local (mlx/ollama) : DEUX appels séparés — une réponse
      conversationnelle en texte simple (rapide, vivante), puis une extraction
      bornée au dernier message (pas de recopie du profil, pas d'hallucination)."""
    if meta is None:
        meta = {}
    prov = llm.provider()
    extra = match_context + rag_context

    if prov == "claude":
        system = build_system_prompt(profile, asked_topics, preferences_summary, extra)
        return llm.chat_structured(system, history, BotTurn, meta=meta)

    # Petit modèle local : réponse d'abord, extraction ensuite.
    meta["provider"] = prov
    meta["fallback"] = False
    reply_system = build_reply_prompt(profile, asked_topics, preferences_summary, extra)
    reply = (llm.chat(reply_system, history, max_tokens=256) or "").strip()
    meta["raw"] = reply
    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    ext = _extract(last_user)
    return BotTurn(reply=reply or "Je t'écoute, raconte-moi un peu plus.",
                   updates=ext.updates, asked_topic=ext.asked_topic,
                   memory_notes=ext.memory_notes,
                   preference_signals=ext.preference_signals)


def apply_updates(profile: Profile, turn: BotTurn) -> None:
    """Applique les informations extraites au profil (sans écraser par du vide)."""
    u = turn.updates
    scalar_fields = ["pseudo", "gender", "birth_place", "city", "department", "country",
                     "profession", "education", "marital_status", "marriage_timeline",
                     "wants_children", "children_count_desired", "religious_practice",
                     "mosque_attendance", "religious_education", "age_estimate",
                     "sought_age_min", "sought_age_max", "sought_location",
                     "sought_religious", "sought_wants_children"]
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
                                  ("sought_qualities", u.sought_qualities),
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

    # Mémoire courte (historique récent) — calibrée selon le moteur :
    #  - Ollama+RAG : fenêtre courte + souvenirs pertinents récupérés (vectoriel) ;
    #  - petit modèle local (mlx) : fenêtre moyenne (rapide et nette) ;
    #  - Claude : fenêtre large.
    # Mémoire longue (portrait + préférences) : toujours réinjectée dans le prompt.
    use_rag = rag.enabled()
    if use_rag:
        window = 8            # mémoire courte + souvenirs RAG (mémoire longue déportée)
    elif llm.provider() == "claude":
        window = config.CONVERSATION_WINDOW
    else:
        window = config.LOCAL_HISTORY_WINDOW
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

    import time as _time
    meta: dict = {}
    _t0 = _time.monotonic()
    turn = converse(profile, history, asked_topics, pref_summary,
                    match_context, rag_context, meta=meta)
    duration = round(_time.monotonic() - _t0, 2)

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

    # Journal d'étude du comportement du modèle
    convlog.record({
        "user_id": user.telegram_id,
        "provider": meta.get("provider"),
        "model": config.MLX_MODEL if meta.get("provider") == "mlx" else
                 (config.OLLAMA_MODEL if meta.get("provider") == "ollama" else config.CLAUDE_MODEL),
        "duration_s": duration,
        "fallback": meta.get("fallback"),
        "user_message": text,
        "reply": turn.reply,
        "asked_topic": turn.asked_topic,
        "updates": {k: v for k, v in turn.updates.model_dump().items()
                    if v not in (None, [], "")},
        "preference_signals": [s.model_dump() for s in turn.preference_signals],
        "memory_notes": turn.memory_notes,
        "completeness": profile.completeness,
        "raw_output": (meta.get("raw") or "")[:2000],
    })

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
