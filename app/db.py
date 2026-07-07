"""Modèles SQLAlchemy et accès base de données (SQLite par défaut)."""
from __future__ import annotations

import datetime as dt
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey,
                        Integer, String, Text, create_engine, event)
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column,
                            relationship, sessionmaker)

from . import config
from .profile_schema import compute_completeness


class Base(DeclarativeBase):
    pass


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(64))
    display_name: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    last_active_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False,
                                              cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship(back_populates="user",
                                                     cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), primary_key=True)

    # Informations générales
    pseudo: Mapped[str | None] = mapped_column(String(64))
    gender: Mapped[str | None] = mapped_column(String(10))          # homme / femme
    birth_date: Mapped[dt.date | None] = mapped_column(Date)
    age_estimate: Mapped[int | None] = mapped_column(Integer)       # si pas de date exacte
    birth_place: Mapped[str | None] = mapped_column(String(128))
    city: Mapped[str | None] = mapped_column(String(128))
    department: Mapped[str | None] = mapped_column(String(64))
    country: Mapped[str | None] = mapped_column(String(64))
    profession: Mapped[str | None] = mapped_column(String(128))
    education: Mapped[str | None] = mapped_column(String(128))

    # Situation personnelle
    marital_status: Mapped[str | None] = mapped_column(String(20))  # celibataire / divorce / veuf

    # Projet
    marriage_timeline: Mapped[str | None] = mapped_column(String(128))
    wants_children: Mapped[bool | None] = mapped_column(Boolean)
    children_count_desired: Mapped[int | None] = mapped_column(Integer)

    # Pratique religieuse
    religious_practice: Mapped[str | None] = mapped_column(Text)
    mosque_attendance: Mapped[str | None] = mapped_column(String(128))
    religious_education: Mapped[str | None] = mapped_column(String(255))

    # Personnalité / intérêts / habitudes (listes JSON)
    personality_traits: Mapped[list | None] = mapped_column(JSON, default=list)
    interests: Mapped[list | None] = mapped_column(JSON, default=list)
    lifestyle_facts: Mapped[list | None] = mapped_column(JSON, default=list)
    memory_notes: Mapped[list | None] = mapped_column(JSON, default=list)

    completeness: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profile")

    @property
    def age(self) -> int | None:
        if self.birth_date:
            today = dt.date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return self.age_estimate

    def refresh_completeness(self) -> int:
        self.completeness = compute_completeness(self)
        return self.completeness


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user / assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="messages")


class AskedQuestion(Base):
    """Mémoire des questions déjà posées pour ne jamais se répéter."""
    __tablename__ = "asked_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), index=True)
    topic: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class Preference(Base):
    """Mémoire structurée des préférences (charte IA §9-10) : chaque signal
    observé dans les réactions renforce une hypothèse, avec niveau de confiance."""
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), index=True)
    # valeurs / vision_couple / personnalite / mode_de_vie / preference_profil
    dimension: Mapped[str] = mapped_column(String(32))
    key: Mapped[str] = mapped_column(String(80))              # ex: "famille", "profil calme"
    orientation: Mapped[str] = mapped_column(String(16))      # favorable / defavorable / reserve
    score: Mapped[int | None] = mapped_column(Integer)        # 0-10 pour les valeurs
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[int] = mapped_column(Integer, default=35)   # % (35 = hypothèse faible)
    last_evidence: Mapped[str | None] = mapped_column(String(300)) # dernier indice observé
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_m_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), index=True)
    user_f_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    details: Mapped[dict | None] = mapped_column(JSON)              # décomposition du score
    # Réponses individuelles : pending / info / accepted / refused / postponed
    response_m: Mapped[str] = mapped_column(String(16), default="pending")
    response_f: Mapped[str] = mapped_column(String(16), default="pending")
    # Statut global : proposed / mutual / refused / expired
    status: Mapped[str] = mapped_column(String(16), default="proposed", index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CommunityPost(Base):
    """Historique des publications d'animation communautaire."""
    __tablename__ = "community_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))   # profil_semaine / question / sondage / quiz / regles / stats
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------------------
_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        if config.DATABASE_URL.startswith("sqlite"):
            db_path = config.DATABASE_URL.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(config.DATABASE_URL,
                                connect_args={"check_same_thread": False}
                                if config.DATABASE_URL.startswith("sqlite") else {})
        if config.DATABASE_URL.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def _fk_on(dbapi_con, _):
                dbapi_con.execute("PRAGMA foreign_keys=ON")
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


@contextmanager
def db_session():
    get_engine()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_or_create_user(session, telegram_id: int, username: str | None = None,
                       display_name: str | None = None) -> User:
    user = session.get(User, telegram_id)
    if user is None:
        user = User(telegram_id=telegram_id, username=username, display_name=display_name,
                    profile=Profile(user_id=telegram_id))
        session.add(user)
        session.flush()
    else:
        if username:
            user.username = username
        if display_name:
            user.display_name = display_name
    user.last_active_at = utcnow()
    return user
