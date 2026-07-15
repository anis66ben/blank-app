"""Mode guidé (sans IA), extraction JSON tolérante, détection des banalités."""
from app import ai, llm
from app.db import (AskedQuestion, Message, User, db_session,
                    get_or_create_user)


def test_provider_none_disables_ai():
    assert llm.provider() == "none"
    assert not llm.enabled()


def test_extract_json_handles_noise():
    assert llm._extract_json('{"a": 1}') == {"a": 1}
    assert llm._extract_json('bla {"a": 1} fin') == {"a": 1}
    assert llm._extract_json('```json\n{"a": {"b": 2}}\n```') == {"a": {"b": 2}}
    assert llm._extract_json("aucun json") is None


def test_trivial_detection():
    for m in ["Salam", "ça va ?", "ok merci", "oui"]:
        assert ai._is_trivial(m)
    for m in ["Je m'appelle Sami", "Je veux une femme proche de sa famille"]:
        assert not ai._is_trivial(m)


def test_scripted_mode_answers_and_builds_profile():
    uid = 770001
    with db_session() as s:
        u = get_or_create_user(s, uid, "g", "G")
        s.add(AskedQuestion(user_id=uid, topic="pseudo"))
    with db_session() as s:
        u = get_or_create_user(s, uid)
        reply = ai.handle_user_message(s, u, "Je m'appelle Nassim")
        assert reply
        assert u.profile.pseudo == "Nassim"
    with db_session() as s:
        for M in (Message, AskedQuestion):
            s.query(M).filter_by(user_id=uid).delete()
        x = s.get(User, uid)
        if x:
            s.delete(x)
