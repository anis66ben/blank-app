"""Mode questionnaire guidé — fonctionne SANS l'API Claude.

Utilisé automatiquement quand ANTHROPIC_API_KEY est vide : le bot pose des
questions prédéfinies (une à la fois, jamais deux fois la même) et analyse les
réponses avec des règles simples. Le profil, l'indice de connaissance, le
matching et le dashboard fonctionnent exactement comme en mode IA.
"""
from __future__ import annotations

import datetime as dt
import random
import re

from .db import AskedQuestion, Message, Profile, User
from .profile_schema import LIST_FIELD_TARGETS, missing_fields

RELAUNCH_MARKER = "[relance automatique"

# ---------------------------------------------------------------------------
# Questions prédéfinies par champ (plusieurs formulations pour varier)
# ---------------------------------------------------------------------------
QUESTIONS: dict[str, list[str]] = {
    "pseudo": ["Comment souhaites-tu que je t'appelle ?"],
    "gender": ["Es-tu un homme ou une femme ?"],
    "birth_date": ["Quelle est ta date de naissance ? (par exemple 12/04/1995 — "
                   "ou simplement ton âge si tu préfères)"],
    "city": ["Dans quelle ville vis-tu actuellement ?"],
    "country": ["Dans quel pays vis-tu ?"],
    "birth_place": ["Où es-tu né(e) ?"],
    "profession": ["Que fais-tu dans la vie ? Quelle est ta profession ?",
                   "Parle-moi de ton travail : que fais-tu comme métier ?"],
    "education": ["Quel est ton parcours d'études ?"],
    "marital_status": ["Quelle est ta situation actuelle : célibataire, divorcé(e) ou veuf(ve) ?"],
    "marriage_timeline": ["Dans quel délai aimerais-tu te marier, idéalement ?",
                          "As-tu une idée du délai dans lequel tu souhaiterais te marier ?"],
    "wants_children": ["Souhaites-tu avoir des enfants, in shâ Allah ?"],
    "children_count_desired": ["Combien d'enfants aimerais-tu avoir, idéalement ?"],
    "religious_practice": ["Parle-moi de ta pratique religieuse au quotidien "
                           "(prières, jeûne, lecture du Coran...)."],
    "mosque_attendance": ["Te rends-tu à la mosquée ? À quelle fréquence ?"],
    "religious_education": ["Suis-tu un apprentissage religieux (cours, mémorisation, lectures) ?"],
    "personality_traits": ["Comment tes proches te décriraient-ils ? Cite 3 ou 4 traits "
                           "de ton caractère (par exemple : calme, sociable, organisé...)."],
    "interests": ["Quels sont tes centres d'intérêt ? Cite-m'en 3 ou 4 "
                  "(voyages, lecture, sport, cuisine...)."],
    "lifestyle_facts": ["Décris-moi tes habitudes de vie en quelques mots "
                        "(sport, alimentation, sommeil, tabac...)."],
}

ACKS = ["Merci !", "Très bien.", "Parfait, c'est noté.", "D'accord, merci.", "C'est noté !"]

PROFILE_DONE = ("Mâchâ'Allah, ton profil est maintenant très complet ! 🎉\n"
                "Je te préviendrai dès qu'un profil compatible sera identifié. "
                "Tu peux consulter ton profil avec /profil.")

CLARIFY = {
    "gender": "Pardon, je n'ai pas bien compris : es-tu un homme ou une femme ?",
    "birth_date": "Je n'ai pas réussi à lire la date. Tu peux l'écrire comme 12/04/1995, "
                  "ou m'indiquer simplement ton âge (par exemple : 29).",
    "marital_status": "Peux-tu préciser : célibataire, divorcé(e) ou veuf(ve) ?",
    "wants_children": "Peux-tu répondre par oui ou par non ?",
    "children_count_desired": "Un chiffre suffit — combien d'enfants aimerais-tu avoir ?",
}


# ---------------------------------------------------------------------------
# Analyse des réponses
# ---------------------------------------------------------------------------
def _clean(text: str, max_len: int = 200) -> str:
    return re.sub(r"\s+", " ", text).strip()[:max_len]


def _parse_pseudo(text: str) -> str | None:
    t = _clean(text, 80)
    m = re.search(r"(?:je m'appelle|je suis|moi c'est|appelle[- ]moi)\s+([A-Za-zÀ-ÿ' -]{2,30})",
                  t, re.IGNORECASE)
    if m:
        return m.group(1).strip().split()[0].capitalize()
    words = [w for w in re.findall(r"[A-Za-zÀ-ÿ']{2,30}", t)
             if w.lower() not in {"salam", "salut", "bonjour", "bonsoir", "wa", "alaykoum",
                                  "assalamou", "aleykoum", "coucou", "hello"}]
    return words[0].capitalize() if words else None


def _parse_gender(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\bhomme\b|\bmasculin\b|\bfr[eè]re\b|\bmonsieur\b", t):
        return "homme"
    if re.search(r"\bfemme\b|\bf[eé]minin\b|\bs[oœ]e?ur\b|\bmadame\b", t):
        return "femme"
    return None


def _parse_birth(text: str, profile: Profile) -> bool:
    """Renseigne birth_date ou age_estimate. True si quelque chose a été compris."""
    m = re.search(r"(\d{1,2})[/\-. ](\d{1,2})[/\-. ](\d{4})", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            profile.birth_date = dt.date(y, mo, d)
            return True
        except ValueError:
            pass
    m = re.search(r"\b(19[4-9]\d|20[01]\d)\b", text)          # année seule
    if m:
        profile.age_estimate = dt.date.today().year - int(m.group(1))
        return True
    m = re.search(r"\b([1-9]\d)\b", text)                      # âge (18-99)
    if m and 18 <= int(m.group(1)) <= 99:
        profile.age_estimate = int(m.group(1))
        return True
    return False


def _parse_marital(text: str) -> str | None:
    t = text.lower()
    if "divorc" in t:
        return "divorce"
    if "veuf" in t or "veuve" in t:
        return "veuf"
    if "c[eé]libataire" and re.search(r"c[eé]libataire|jamais mari|pas mari", t):
        return "celibataire"
    return None


def _parse_yes_no(text: str) -> bool | None:
    t = text.lower()
    if re.search(r"\bnon\b|\bpas vraiment\b|\bje ne (veux|souhaite) pas\b", t):
        return False
    if re.search(r"\boui\b|\bbien s[uû]r\b|in ?ch[aâ]+llah|in ?sh[aâ]+ allah|"
                 r"\bj'aimerais\b|\babsolument\b|\bavec plaisir\b|\bsi dieu\b", t):
        return True
    return None


def _parse_count(text: str) -> int | None:
    words = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6}
    t = text.lower()
    for w, n in words.items():
        if re.search(rf"\b{w}\b", t):
            return n
    m = re.search(r"\b(\d{1,2})\b", t)
    if m and 0 <= int(m.group(1)) <= 12:
        return int(m.group(1))
    return None


def _parse_list(text: str) -> list[str]:
    parts = re.split(r",|;|\n|·|•| et ", text)
    items = []
    for part in parts:
        item = _clean(part, 40).strip(".!… ").lower()
        item = re.sub(r"^(je suis|je fais|j'aime( bien)?|plut[oô]t|très|assez)\s+", "", item)
        if 2 <= len(item) <= 40:
            items.append(item)
    return items[:6]


def _store_free_text(profile: Profile, field: str, text: str) -> bool:
    value = _clean(text)
    value = re.sub(r"^(je vis |j'habite |je suis n[eé]e? |je suis |je travaille comme |"
                   r"je travaille dans |je fais |j'ai fait |j'aimerais |c'est |"
                   r"dans |à |en |au |aux |un |une )+",
                   "", value, flags=re.IGNORECASE).strip()
    if len(value) < 2:
        return False
    setattr(profile, field, value[:200].capitalize() if field in
            ("city", "country", "birth_place", "department") else value)
    return True


def parse_answer(profile: Profile, topic: str, text: str) -> bool:
    """Applique la réponse au champ visé. Renvoie True si comprise."""
    if topic == "pseudo":
        value = _parse_pseudo(text)
        if value:
            profile.pseudo = value
            return True
        return False
    if topic == "gender":
        value = _parse_gender(text)
        if value:
            profile.gender = value
            return True
        return False
    if topic == "birth_date":
        return _parse_birth(text, profile)
    if topic == "marital_status":
        value = _parse_marital(text)
        if value:
            profile.marital_status = value
            return True
        return False
    if topic == "wants_children":
        value = _parse_yes_no(text)
        if value is not None:
            profile.wants_children = value
            return True
        return False
    if topic == "children_count_desired":
        value = _parse_count(text)
        if value is not None:
            profile.children_count_desired = value
            return True
        return False
    if topic in LIST_FIELD_TARGETS:
        items = _parse_list(text)
        if items:
            current = list(getattr(profile, topic) or [])
            lowered = {i.lower() for i in current}
            current += [i for i in items if i.lower() not in lowered]
            setattr(profile, topic, current[:40])
            return True
        return False
    # Champs en texte libre
    return _store_free_text(profile, topic, text)


# ---------------------------------------------------------------------------
# Tour de conversation
# ---------------------------------------------------------------------------
def _ack_for(profile: Profile, topic: str) -> str:
    if topic == "pseudo" and profile.pseudo:
        return f"Enchanté, {profile.pseudo} !"
    if topic == "city" and profile.city:
        return f"{profile.city}, très bien !"
    return random.choice(ACKS)


def next_question(session, user: User) -> str | None:
    """Choisit la prochaine question (champ manquant jamais demandé), la mémorise."""
    asked = {q.topic for q in session.query(AskedQuestion)
             .filter(AskedQuestion.user_id == user.telegram_id).all()}
    for field in missing_fields(user.profile):
        if field in QUESTIONS and field not in asked:
            session.add(AskedQuestion(user_id=user.telegram_id, topic=field))
            return random.choice(QUESTIONS[field])
    return None


def handle_user_message(session, user: User, text: str) -> str:
    """Équivalent scripté de ai.handle_user_message : même signature, même effet."""
    profile = user.profile
    is_relaunch = text.startswith(RELAUNCH_MARKER)
    if not is_relaunch:
        session.add(Message(user_id=user.telegram_id, role="user", content=text))

    parts: list[str] = []
    if not is_relaunch:
        pending = (session.query(AskedQuestion)
                   .filter(AskedQuestion.user_id == user.telegram_id)
                   .order_by(AskedQuestion.created_at.desc(), AskedQuestion.id.desc())
                   .first())
        if pending and pending.topic in QUESTIONS:
            understood = parse_answer(profile, pending.topic, text)
            profile.refresh_completeness()
            if understood:
                parts.append(_ack_for(profile, pending.topic))
            elif pending.topic in CLARIFY:
                # Redemande avec clarification, sans passer à la suite
                reply = CLARIFY[pending.topic]
                session.add(Message(user_id=user.telegram_id, role="assistant", content=reply))
                return reply
            else:
                parts.append(random.choice(ACKS))
    else:
        parts.append("Assalamou alaykoum ! J'espère que tu vas bien. "
                     "J'aimerais continuer à faire connaissance avec toi. 😊")

    question = next_question(session, user)
    if question:
        parts.append(question)
    else:
        parts.append(PROFILE_DONE)

    reply = " ".join(parts)
    session.add(Message(user_id=user.telegram_id, role="assistant", content=reply))
    return reply


# ---------------------------------------------------------------------------
# Contenus communautaires statiques (remplacent la génération IA)
# ---------------------------------------------------------------------------
QUESTION_BANK = [
    "Quelle qualité vous semble la plus importante chez un(e) futur(e) époux(se), et pourquoi ?",
    "Pour vous, c'est quoi une vie de couple réussie ?",
    "Quelle place la famille élargie devrait-elle avoir dans un couple ?",
    "Quel est le plus beau conseil qu'on vous ait donné sur le mariage ?",
    "Préféreriez-vous vivre en ville ou à la campagne après le mariage ? Pourquoi ?",
    "Quelle habitude aimeriez-vous construire à deux (lecture, sport, apprentissage du Coran...) ?",
    "Selon vous, comment bien gérer les désaccords dans un couple ?",
]

QUIZ_BANK = [
    "Quel est le premier pilier de l'islam ?\nA) La prière\nB) L'attestation de foi\n"
    "C) Le jeûne\nD) La zakat\nRéponse : B",
    "Combien de sourates compte le Coran ?\nA) 99\nB) 110\nC) 114\nD) 120\nRéponse : C",
    "Quelle sourate est surnommée « le cœur du Coran » ?\nA) Ya-Sin\nB) Al-Fatiha\n"
    "C) Al-Ikhlas\nD) Al-Mulk\nRéponse : A",
    "Quel mois précède le Ramadan ?\nA) Rajab\nB) Chawwal\nC) Cha'bane\nD) Mouharram\nRéponse : C",
]

RULES_TEXT = ("• Respect et bienveillance entre tous les membres\n"
              "• Pudeur dans les échanges, conformément à notre éthique\n"
              "• Pas de contact privé non sollicité\n"
              "• Signalez tout comportement déplacé aux administrateurs\n"
              "Qu'Allah préserve ce groupe et ses membres. 🤲")


def static_community_text(kind: str) -> str:
    if kind == "quiz":
        return random.choice(QUIZ_BANK)
    if kind == "rappel_regles":
        return RULES_TEXT
    return random.choice(QUESTION_BANK)
