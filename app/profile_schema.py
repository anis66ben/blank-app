"""Schéma du profil : catégories, pondérations de complétude et modèles Pydantic
utilisés pour l'extraction structurée pendant les conversations."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Indice de connaissance du profil (0-100)
# Chaque champ rempli rapporte son poids ; la somme des poids fait 100.
# ---------------------------------------------------------------------------
COMPLETENESS_WEIGHTS = {
    # Informations générales (30)
    "pseudo": 3,
    "gender": 5,
    "birth_date": 5,
    "birth_place": 2,
    "city": 4,
    "country": 3,
    "profession": 4,
    "education": 4,
    # Situation personnelle (6)
    "marital_status": 6,
    # Projet (18)
    "marriage_timeline": 6,
    "wants_children": 6,
    "children_count_desired": 6,
    # Pratique religieuse (18)
    "religious_practice": 8,
    "mosque_attendance": 5,
    "religious_education": 5,
    # Personnalité & centres d'intérêt (28)
    "personality_traits": 12,   # complet à partir de 4 traits
    "interests": 10,            # complet à partir de 4 centres d'intérêt
    "lifestyle_facts": 6,       # complet à partir de 3 habitudes de vie
}

LIST_FIELD_TARGETS = {
    "personality_traits": 4,
    "interests": 4,
    "lifestyle_facts": 3,
}

# Ordre de collecte progressive : le bot enrichit les catégories dans cet ordre.
CATEGORY_FIELDS = {
    "identite": ["pseudo", "gender", "birth_date", "city", "country", "birth_place",
                 "profession", "education"],
    "situation": ["marital_status"],
    "projet": ["marriage_timeline", "wants_children", "children_count_desired"],
    "religion": ["religious_practice", "mosque_attendance", "religious_education"],
    "personnalite": ["personality_traits"],
    "interets": ["interests", "lifestyle_facts"],
}

CATEGORY_LABELS = {
    "identite": "identité générale",
    "situation": "situation personnelle",
    "projet": "projet de mariage et de famille",
    "religion": "pratique religieuse",
    "personnalite": "personnalité",
    "interets": "centres d'intérêt et habitudes de vie",
}

FIELD_LABELS = {
    "pseudo": "prénom ou pseudonyme",
    "gender": "sexe",
    "birth_date": "date de naissance",
    "birth_place": "lieu de naissance",
    "city": "ville actuelle",
    "department": "département",
    "country": "pays",
    "profession": "profession",
    "education": "études",
    "marital_status": "situation personnelle",
    "marriage_timeline": "délai souhaité pour le mariage",
    "wants_children": "souhait d'avoir des enfants",
    "children_count_desired": "nombre d'enfants souhaité",
    "religious_practice": "pratique religieuse quotidienne",
    "mosque_attendance": "fréquentation de la mosquée",
    "religious_education": "apprentissage religieux",
    "personality_traits": "traits de personnalité",
    "interests": "centres d'intérêt",
    "lifestyle_facts": "habitudes de vie",
}


def compute_completeness(profile) -> int:
    """Calcule l'indice de connaissance (0-100) à partir d'une ligne Profile."""
    score = 0.0
    for field, weight in COMPLETENESS_WEIGHTS.items():
        value = getattr(profile, field, None)
        if field in LIST_FIELD_TARGETS:
            items = value or []
            target = LIST_FIELD_TARGETS[field]
            score += weight * min(len(items), target) / target
        elif value is not None and str(value).strip() != "":
            score += weight
    return round(min(score, 100))


def missing_fields(profile) -> list[str]:
    """Champs encore inconnus, dans l'ordre de collecte progressive."""
    missing = []
    for fields in CATEGORY_FIELDS.values():
        for field in fields:
            value = getattr(profile, field, None)
            if field in LIST_FIELD_TARGETS:
                if len(value or []) < LIST_FIELD_TARGETS[field]:
                    missing.append(field)
            elif value is None or str(value).strip() == "":
                missing.append(field)
    return missing


# ---------------------------------------------------------------------------
# Modèles Pydantic pour l'extraction structurée (sortie du modèle Claude)
# ---------------------------------------------------------------------------
class ProfileUpdates(BaseModel):
    """Informations factuelles apprises dans le dernier message de l'utilisateur.
    Ne renseigner un champ QUE si l'utilisateur l'a réellement communiqué."""
    pseudo: Optional[str] = None
    gender: Optional[str] = Field(None, description="'homme' ou 'femme'")
    birth_date: Optional[str] = Field(None, description="Date ISO AAAA-MM-JJ si connue, sinon null")
    age_estimate: Optional[int] = Field(None, description="Âge en années si donné sans date de naissance")
    birth_place: Optional[str] = None
    city: Optional[str] = None
    department: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    education: Optional[str] = None
    marital_status: Optional[str] = Field(None, description="'celibataire', 'divorce' ou 'veuf'")
    marriage_timeline: Optional[str] = Field(None, description="Délai souhaité, ex: 'dans l'année'")
    wants_children: Optional[bool] = None
    children_count_desired: Optional[int] = None
    religious_practice: Optional[str] = Field(None, description="Description de la pratique quotidienne")
    mosque_attendance: Optional[str] = None
    religious_education: Optional[str] = None
    personality_traits: List[str] = Field(default_factory=list,
                                          description="Nouveaux traits observés ou déclarés")
    interests: List[str] = Field(default_factory=list)
    lifestyle_facts: List[str] = Field(default_factory=list,
                                       description="Habitudes de vie, ex: 'sportif', 'ne fume pas'")


class PreferenceSignal(BaseModel):
    """Signal implicite ou explicite détecté dans une réaction de l'utilisateur
    (charte IA §7-8). N'émettre un signal QUE s'il ressort réellement du message."""
    dimension: str = Field(description="'valeurs', 'vision_couple', 'personnalite', "
                                       "'mode_de_vie' ou 'preference_profil'")
    cle: str = Field(description="Objet du signal, court et réutilisable, "
                                 "ex: 'famille', 'profil calme', 'distance geographique'")
    orientation: str = Field(description="'favorable', 'defavorable' ou 'reserve'")
    score: Optional[int] = Field(None, description="Importance 0-10, surtout pour les valeurs")
    indice: Optional[str] = Field(None, description="Citation courte du message qui fonde ce signal")


class BotTurn(BaseModel):
    """Réponse complète du bot pour un tour de conversation."""
    reply: str = Field(description="Message à envoyer à l'utilisateur, en français, chaleureux et naturel")
    updates: ProfileUpdates = Field(default_factory=ProfileUpdates)
    asked_topic: Optional[str] = Field(
        None, description="Clé du champ de profil sur lequel porte la question posée dans reply, s'il y en a une")
    memory_notes: List[str] = Field(
        default_factory=list,
        description="Faits importants à mémoriser pour les prochaines conversations")
    preference_signals: List[PreferenceSignal] = Field(
        default_factory=list,
        description="Signaux de préférence détectés dans la réaction (analyse implicite, charte §7)")
