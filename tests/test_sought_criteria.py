"""Critères recherchés explicites (P2) : scoring et pondérations configurables."""
import datetime as dt

import app.config as config
from app import matching
from app.db import Profile


def _p(uid, gender, **kw):
    p = Profile(user_id=uid, gender=gender, birth_date=dt.date(1995, 1, 1),
                city="Lyon", country="France", wants_children=True,
                children_count_desired=2, religious_practice="Prie ses 5 prières",
                personality_traits=["calme", "organise"], interests=["lecture"],
                lifestyle_facts=["sport"], completeness=80)
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def test_sought_rewards_matching_criteria():
    seeker = _p(1, "homme", sought_age_min=25, sought_age_max=35,
                sought_wants_children=True, sought_religious="priere pratiquant",
                sought_qualities=["calme"])
    cand = _p(2, "femme")
    pts, reasons = matching.sought_score(seeker, cand)
    assert pts > 0
    assert any("âge" in r for r in reasons)


def test_sought_penalizes_age_out_of_range():
    seeker = _p(1, "homme", sought_age_min=45, sought_age_max=55)
    cand = _p(2, "femme")  # 30 ans
    pts, _ = matching.sought_score(seeker, cand)
    assert pts < 0


def test_sought_neutral_when_no_criteria():
    seeker = _p(1, "homme")
    cand = _p(2, "femme")
    pts, reasons = matching.sought_score(seeker, cand)
    assert pts == 0 and reasons == []


def test_weights_are_configurable(monkeypatch):
    pm = _p(1, "homme")
    pf = _p(2, "femme")
    base = dict(config.MATCH_WEIGHTS)
    _, d1 = matching.compatibility(pm, pf)
    boosted = dict(base, localisation=30.0)
    monkeypatch.setattr(config, "MATCH_WEIGHTS", boosted)
    _, d2 = matching.compatibility(pm, pf)
    assert d2["localisation"] > d1["localisation"]
