"""Schéma de profil : indice de complétude et champs manquants."""
import datetime as dt

from app.db import Profile
from app.profile_schema import compute_completeness, missing_fields


def _profile(**kw):
    p = Profile(user_id=1)
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def test_completeness_empty_is_zero():
    assert compute_completeness(_profile()) == 0


def test_completeness_increases_with_fields():
    p = _profile(pseudo="Sami", gender="homme", city="Lyon", country="France",
                 birth_date=dt.date(1995, 1, 1))
    c = compute_completeness(p)
    assert 0 < c < 100


def test_completeness_capped_at_100():
    p = _profile(pseudo="A", gender="homme", birth_date=dt.date(1990, 1, 1),
                 birth_place="Paris", city="Lyon", country="France",
                 profession="X", education="Y", marital_status="celibataire",
                 marriage_timeline="1 an", wants_children=True,
                 children_count_desired=2, religious_practice="prie",
                 mosque_attendance="vendredi", religious_education="cours",
                 personality_traits=["a", "b", "c", "d"],
                 interests=["a", "b", "c", "d"],
                 lifestyle_facts=["a", "b", "c"])
    assert compute_completeness(p) == 100


def test_missing_fields_lists_unknowns():
    p = _profile(pseudo="Sami")
    missing = missing_fields(p)
    assert "gender" in missing and "pseudo" not in missing
