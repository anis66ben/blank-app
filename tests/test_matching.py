"""Moteur de matching : filtres obligatoires, score, exclusion par signalement."""
import datetime as dt

import pytest

from app import matching
from app.db import (AskedQuestion, Match, MemoryChunk, Message, Preference,
                    Profile, Report, User, db_session, get_or_create_user)


def _mk(session, uid, gender, **kw):
    u = get_or_create_user(session, uid, f"u{uid}", str(uid))
    p = u.profile
    p.gender = gender
    p.birth_date = kw.get("birth_date", dt.date(1995, 1, 1))
    p.city = kw.get("city", "Lyon")
    p.country = kw.get("country", "France")
    p.wants_children = True
    p.children_count_desired = 2
    p.religious_practice = "Prie régulièrement"
    p.personality_traits = ["calme"]
    p.interests = ["lecture"]
    p.marital_status = "celibataire"
    p.refresh_completeness()
    return p


@pytest.fixture
def two_users():
    ids = (990001, 990002)
    with db_session() as s:
        _mk(s, ids[0], "homme")
        _mk(s, ids[1], "femme")
    yield ids
    with db_session() as s:
        for uid in ids:
            for M in (MemoryChunk, Preference, AskedQuestion, Message):
                s.query(M).filter_by(user_id=uid).delete()
            s.query(Report).filter((Report.reporter_id == uid) | (Report.reported_id == uid)).delete()
            s.query(Match).filter((Match.user_m_id == uid) | (Match.user_f_id == uid)).delete()
            s.query(Profile).filter_by(user_id=uid).delete()
            u = s.get(User, uid)
            if u:
                s.delete(u)


def test_hard_filters_reject_same_gender():
    pm = Profile(user_id=1, gender="homme", birth_date=dt.date(1995, 1, 1), completeness=80)
    pm2 = Profile(user_id=2, gender="homme", birth_date=dt.date(1995, 1, 1), completeness=80)
    assert not matching.hard_filters_ok(pm, pm2)


def test_hard_filters_reject_large_age_gap():
    pm = Profile(user_id=1, gender="homme", birth_date=dt.date(1970, 1, 1), completeness=80)
    pf = Profile(user_id=2, gender="femme", birth_date=dt.date(2000, 1, 1), completeness=80)
    assert not matching.hard_filters_ok(pm, pf)


def test_compatible_pair_creates_match(two_users):
    with db_session() as s:
        created = matching.find_new_matches(s)
        pairs = {(m.user_m_id, m.user_f_id) for m in created}
    assert two_users in pairs


def test_report_excludes_pair(two_users):
    with db_session() as s:
        matching.find_new_matches(s)
        s.query(Match).filter(Match.user_m_id == two_users[0]).delete()
        s.add(Report(reporter_id=two_users[1], reported_id=two_users[0], reason="test"))
    with db_session() as s:
        created = matching.find_new_matches(s)
        pairs = {(m.user_m_id, m.user_f_id) for m in created}
    assert two_users not in pairs


def test_response_state_machine(two_users):
    with db_session() as s:
        matching.find_new_matches(s)
        m = s.query(Match).filter(Match.user_m_id == two_users[0]).first()
        matching.register_response(s, m, two_users[0], "accepted")
        assert m.status == "proposed"
        matching.register_response(s, m, two_users[1], "accepted")
        assert m.status == "mutual"
