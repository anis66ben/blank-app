"""Insère des données de démonstration pour tester le matching et le dashboard.

Usage :  python -m scripts.seed_demo
"""
from __future__ import annotations

import datetime as dt

from app import matching
from app.db import Message, Profile, User, db_session, get_or_create_user

DEMO = [
    dict(id=1001, pseudo="Yassine", gender="homme", birth=dt.date(1993, 4, 12),
         city="Lyon", dept="69", country="France", job="Ingénieur logiciel",
         edu="Master informatique", status="celibataire", timeline="dans l'année",
         children=True, n_children=3, practice="Prie ses 5 prières, pratiquant régulier",
         mosque="Vendredi et parfois en semaine", learning="Cours de tajwid le week-end",
         traits=["calme", "organisé", "sportif", "à l'écoute"],
         interests=["voyages", "lecture", "randonnée", "cuisine"],
         lifestyle=["ne fume pas", "sportif", "lève-tôt"]),
    dict(id=1002, pseudo="Amine", gender="homme", birth=dt.date(1988, 9, 3),
         city="Paris", dept="75", country="France", job="Commerçant",
         edu="BTS commerce", status="divorce", timeline="pas de délai précis",
         children=True, n_children=2, practice="Prie régulièrement, en apprentissage",
         mosque="Vendredi", learning="Lit le Coran seul",
         traits=["sociable", "humour", "généreux"],
         interests=["football", "voyages", "restaurants"],
         lifestyle=["ne fume pas"]),
    dict(id=1003, pseudo="Karim", gender="homme", birth=dt.date(1996, 1, 25),
         city="Marseille", dept="13", country="France", job="Infirmier",
         edu="IFSI", status="celibataire", timeline="dans les deux ans",
         children=None, n_children=None, practice=None,
         mosque=None, learning=None,
         traits=["patient"], interests=["natation"], lifestyle=[]),
    dict(id=2001, pseudo="Imane", gender="femme", birth=dt.date(1995, 7, 8),
         city="Lyon", dept="69", country="France", job="Enseignante",
         edu="Master MEEF", status="celibataire", timeline="dans l'année",
         children=True, n_children=3, practice="Prie ses 5 prières, porte le hijab",
         mosque="Cours du dimanche", learning="Mémorisation du Coran en cours",
         traits=["calme", "organisée", "à l'écoute", "douce"],
         interests=["lecture", "voyages", "pâtisserie", "randonnée"],
         lifestyle=["ne fume pas", "lève-tôt"]),
    dict(id=2002, pseudo="Sarah", gender="femme", birth=dt.date(1990, 11, 30),
         city="Paris", dept="75", country="France", job="Pharmacienne",
         edu="Doctorat pharmacie", status="celibataire", timeline="rapidement",
         children=True, n_children=2, practice="Prie régulièrement",
         mosque="Occasionnellement", learning="Podcasts et lectures",
         traits=["sociable", "humour", "dynamique"],
         interests=["voyages", "cuisine", "musées"],
         lifestyle=["ne fume pas", "sportive"]),
    dict(id=2003, pseudo="Khadija", gender="femme", birth=dt.date(1999, 2, 14),
         city="Lille", dept="59", country="France", job="Étudiante",
         edu="Licence droit", status="celibataire", timeline=None,
         children=None, n_children=None, practice="Prie ses 5 prières",
         mosque=None, learning=None,
         traits=["réservée", "studieuse"], interests=["lecture"], lifestyle=[]),
]


def main() -> None:
    with db_session() as session:
        for d in DEMO:
            user = get_or_create_user(session, d["id"], username=f"demo_{d['pseudo'].lower()}",
                                      display_name=d["pseudo"])
            p: Profile = user.profile
            p.pseudo = d["pseudo"]
            p.gender = d["gender"]
            p.birth_date = d["birth"]
            p.city = d["city"]
            p.department = d["dept"]
            p.country = d["country"]
            p.profession = d["job"]
            p.education = d["edu"]
            p.marital_status = d["status"]
            p.marriage_timeline = d["timeline"]
            p.wants_children = d["children"]
            p.children_count_desired = d["n_children"]
            p.religious_practice = d["practice"]
            p.mosque_attendance = d["mosque"]
            p.religious_education = d["learning"]
            p.personality_traits = d["traits"]
            p.interests = d["interests"]
            p.lifestyle_facts = d["lifestyle"]
            p.refresh_completeness()
            if not session.query(Message).filter(Message.user_id == d["id"]).count():
                session.add(Message(user_id=d["id"], role="assistant",
                                    content="Assalamou alaykoum, bienvenue !"))
                session.add(Message(user_id=d["id"], role="user",
                                    content=f"Wa alaykoum salam, je m'appelle {d['pseudo']}."))
        session.flush()
        created = matching.find_new_matches(session)
        print(f"{len(DEMO)} profils de démonstration insérés.")
        for m in created:
            print(f"Match créé : {m.user_m_id} ↔ {m.user_f_id} — score {m.score}")
        if not created:
            print("Aucun nouveau match (déjà créés ou score sous le seuil).")


if __name__ == "__main__":
    main()
