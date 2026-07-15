"""Backend d'administration local : API REST FastAPI + interface web statique.

Lancement :  python -m app.webadmin   (ou : uvicorn app.webadmin:app --port 8000)
Interface :  http://localhost:8000    (mot de passe : ADMIN_PASSWORD du .env)
"""
from __future__ import annotations

import datetime as dt
import secrets
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import config
from .db import (AskedQuestion, Match, Message, Preference, Profile, User,
                 db_session, utcnow)

app = FastAPI(title="Admin — Plateforme de rencontre", docs_url="/api/docs")
security = HTTPBasic(auto_error=False)
STATIC_DIR = Path(__file__).parent / "static"


def require_admin(credentials: Optional[HTTPBasicCredentials] = Depends(security)) -> None:
    """Authentification HTTP Basic : n'importe quel identifiant, mot de passe
    = ADMIN_PASSWORD. Si ADMIN_PASSWORD est vide, accès libre (développement)."""
    if not config.ADMIN_PASSWORD:
        return
    if credentials is None or not secrets.compare_digest(
            credentials.password.encode(), config.ADMIN_PASSWORD.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Mot de passe incorrect",
                            headers={"WWW-Authenticate": "Basic realm=admin"})


def _user_row(user: User, p: Profile) -> dict:
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "pseudo": p.pseudo or user.display_name,
        "gender": p.gender,
        "age": p.age,
        "birth_date": p.birth_date.isoformat() if p.birth_date else None,
        "birth_place": p.birth_place,
        "city": p.city,
        "department": p.department,
        "country": p.country,
        "profession": p.profession,
        "education": p.education,
        "marital_status": p.marital_status,
        "religious_practice": p.religious_practice,
        "completeness": p.completeness,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "last_active_at": user.last_active_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------
@app.get("/api/stats", dependencies=[Depends(require_admin)])
def stats() -> dict:
    with db_session() as session:
        users = session.query(User).all()
        profiles = {p.user_id: p for p in session.query(Profile).all()}
        matches = session.query(Match).all()
        week_ago = utcnow() - dt.timedelta(days=7)

        completeness_bins = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
        for p in profiles.values():
            c = p.completeness or 0
            idx = min(c // 20, 4)
            completeness_bins[list(completeness_bins)[idx]] += 1

        signups: dict[str, int] = {}
        for u in users:
            week = u.created_at.strftime("%Y-S%W")
            signups[week] = signups.get(week, 0) + 1

        responded = [m for m in matches if m.status in ("mutual", "refused")]
        mutual = sum(1 for m in matches if m.status == "mutual")
        return {
            "total_users": len(users),
            "men": sum(1 for p in profiles.values() if p.gender == "homme"),
            "women": sum(1 for p in profiles.values() if p.gender == "femme"),
            "active": sum(1 for u in users if u.is_active),
            "incomplete": sum(1 for p in profiles.values() if (p.completeness or 0) < 50),
            "new_7d": sum(1 for u in users if u.created_at >= week_ago),
            "matches_total": len(matches),
            "matches_mutual": mutual,
            "acceptance_rate": round(mutual / len(responded) * 100) if responded else None,
            "completeness_bins": completeness_bins,
            "signups_by_week": dict(sorted(signups.items())),
        }


# ---------------------------------------------------------------------------
# Utilisateurs : liste filtrée + fiche détaillée + conversation
# ---------------------------------------------------------------------------
@app.get("/api/users", dependencies=[Depends(require_admin)])
def list_users(search: str = "", gender: str = "", marital_status: str = "",
               city: str = "", department: str = "", country: str = "",
               profession: str = "", status_filter: str = Query("", alias="status"),
               age_min: int = 18, age_max: int = 99,
               completeness_min: int = 0) -> list[dict]:
    with db_session() as session:
        rows = (session.query(User, Profile)
                .join(Profile, Profile.user_id == User.telegram_id).all())
        out = []
        for user, p in rows:
            if gender and p.gender != gender:
                continue
            if marital_status and p.marital_status != marital_status:
                continue
            if status_filter == "actif" and not user.is_active:
                continue
            if status_filter == "inactif" and user.is_active:
                continue
            for value, field in [(city, p.city), (department, p.department),
                                 (country, p.country), (profession, p.profession)]:
                if value and value.lower() not in (field or "").lower():
                    break
            else:
                if p.age is not None and not (age_min <= p.age <= age_max):
                    continue
                if (p.completeness or 0) < completeness_min:
                    continue
                if search:
                    haystack = " ".join(filter(None, [
                        p.pseudo, user.username, user.display_name,
                        str(user.telegram_id)])).lower()
                    if search.lower() not in haystack:
                        continue
                out.append(_user_row(user, p))
        out.sort(key=lambda r: r["created_at"], reverse=True)
        return out


@app.get("/api/users/{telegram_id}", dependencies=[Depends(require_admin)])
def user_detail(telegram_id: int) -> dict:
    with db_session() as session:
        user = session.get(User, telegram_id)
        if user is None:
            raise HTTPException(404, "Utilisateur introuvable")
        p = user.profile
        topics = [q.topic for q in session.query(AskedQuestion)
                  .filter(AskedQuestion.user_id == telegram_id).all()]
        prefs = (session.query(Preference)
                 .filter(Preference.user_id == telegram_id)
                 .order_by(Preference.confidence.desc()).all())
        row = _user_row(user, p)
        row.update({
            "marriage_timeline": p.marriage_timeline,
            "wants_children": p.wants_children,
            "children_count_desired": p.children_count_desired,
            "mosque_attendance": p.mosque_attendance,
            "religious_education": p.religious_education,
            "personality_traits": p.personality_traits or [],
            "interests": p.interests or [],
            "lifestyle_facts": p.lifestyle_facts or [],
            "memory_notes": p.memory_notes or [],
            "asked_topics": topics,
            "sought": {
                "age_min": p.sought_age_min, "age_max": p.sought_age_max,
                "location": p.sought_location, "religious": p.sought_religious,
                "wants_children": p.sought_wants_children,
                "qualities": p.sought_qualities or [],
            },
            "preferences": [{
                "dimension": pr.dimension, "key": pr.key,
                "orientation": pr.orientation, "score": pr.score,
                "occurrences": pr.occurrences, "confidence": pr.confidence,
                "last_evidence": pr.last_evidence,
            } for pr in prefs],
        })
        return row


@app.get("/api/users/{telegram_id}/messages", dependencies=[Depends(require_admin)])
def user_messages(telegram_id: int) -> list[dict]:
    with db_session() as session:
        if session.get(User, telegram_id) is None:
            raise HTTPException(404, "Utilisateur introuvable")
        msgs = (session.query(Message).filter(Message.user_id == telegram_id)
                .order_by(Message.created_at.asc(), Message.id.asc()).all())
        return [{"role": m.role, "content": m.content,
                 "created_at": m.created_at.isoformat()} for m in msgs]


# ---------------------------------------------------------------------------
# Matchs
# ---------------------------------------------------------------------------
@app.get("/api/matches", dependencies=[Depends(require_admin)])
def list_matches(status_filter: str = Query("", alias="status")) -> list[dict]:
    with db_session() as session:
        names = {p.user_id: (p.pseudo or str(p.user_id))
                 for p in session.query(Profile).all()}
        rows = session.query(Match).order_by(Match.created_at.desc()).all()
        out = []
        for m in rows:
            if status_filter and m.status != status_filter:
                continue
            out.append({
                "id": m.id,
                "user_m_id": m.user_m_id, "user_m": names.get(m.user_m_id),
                "user_f_id": m.user_f_id, "user_f": names.get(m.user_f_id),
                "score": m.score,
                "response_m": m.response_m, "response_f": m.response_f,
                "status": m.status,
                "details": m.details,
                "created_at": m.created_at.isoformat(),
            })
        return out


# ---------------------------------------------------------------------------
# Interface web
# ---------------------------------------------------------------------------
@app.get("/", dependencies=[Depends(require_admin)], include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


def main() -> None:
    import os

    import uvicorn
    host = os.getenv("WEBADMIN_HOST", "127.0.0.1")
    port = int(os.getenv("WEBADMIN_PORT", "8000"))
    uvicorn.run("app.webadmin:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
