"""RGPD : plafond quotidien, export, suppression totale."""
from app import privacy
from app.db import (AskedQuestion, MemoryChunk, Message, Preference, User,
                    db_session, get_or_create_user, utcnow)


def _seed(session, uid):
    u = get_or_create_user(session, uid, "p", "P")
    u.consented_at = utcnow()
    for i in range(3):
        session.add(Message(user_id=uid, role="user", content=f"m{i}"))
    session.add(Preference(user_id=uid, dimension="valeurs", key="famille",
                           orientation="favorable", confidence=60))


def test_count_messages_today():
    uid = 880001
    with db_session() as s:
        _seed(s, uid)
    with db_session() as s:
        assert privacy.count_messages_today(s, uid) == 3
    _cleanup(uid)


def test_export_contains_profile():
    uid = 880002
    with db_session() as s:
        _seed(s, uid)
    with db_session() as s:
        exp = privacy.export_data(s, uid)
    assert str(uid) in exp and "famille" in exp
    _cleanup(uid)


def test_delete_removes_everything():
    uid = 880003
    with db_session() as s:
        _seed(s, uid)
    with db_session() as s:
        assert privacy.delete_data(s, uid) is True
    with db_session() as s:
        assert s.get(User, uid) is None
        assert s.query(Message).filter_by(user_id=uid).count() == 0
        assert s.query(Preference).filter_by(user_id=uid).count() == 0


def _cleanup(uid):
    with db_session() as s:
        for M in (MemoryChunk, Preference, AskedQuestion, Message):
            s.query(M).filter_by(user_id=uid).delete()
        u = s.get(User, uid)
        if u:
            s.delete(u)
