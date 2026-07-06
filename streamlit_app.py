"""Tableau de bord administrateur — supervision des utilisateurs, matchs,
conversations et statistiques.

Lancement :  streamlit run streamlit_app.py
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from app import config
from app.db import (AskedQuestion, Match, Message, Profile, User, db_session,
                    utcnow)

st.set_page_config(page_title="Admin — Rencontres", page_icon="🌙", layout="wide")


# ---------------------------------------------------------------------------
# Authentification simple
# ---------------------------------------------------------------------------
def check_auth() -> bool:
    if not config.ADMIN_PASSWORD:
        st.warning("⚠️ ADMIN_PASSWORD n'est pas défini dans .env — accès libre "
                   "(à réserver au développement).")
        return True
    if st.session_state.get("authed"):
        return True
    st.title("🌙 Tableau de bord administrateur")
    with st.form("login"):
        pwd = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter"):
            if pwd == config.ADMIN_PASSWORD:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
    return False


if not check_auth():
    st.stop()


# ---------------------------------------------------------------------------
# Chargement des données
# ---------------------------------------------------------------------------
@st.cache_data(ttl=30)
def load_users_df() -> pd.DataFrame:
    with db_session() as session:
        rows = (session.query(User, Profile)
                .join(Profile, Profile.user_id == User.telegram_id).all())
        data = []
        for user, p in rows:
            data.append({
                "ID Telegram": user.telegram_id,
                "Pseudo Telegram": user.username,
                "Prénom": p.pseudo or user.display_name,
                "Sexe": p.gender,
                "Âge": p.age,
                "Lieu de naissance": p.birth_place,
                "Ville": p.city,
                "Département": p.department,
                "Pays": p.country,
                "Profession": p.profession,
                "Études": p.education,
                "Situation": p.marital_status,
                "Pratique religieuse": p.religious_practice,
                "Complétude (%)": p.completeness,
                "Actif": "oui" if user.is_active else "non",
                "Inscription": user.created_at,
                "Dernière activité": user.last_active_at,
            })
    return pd.DataFrame(data)


@st.cache_data(ttl=30)
def load_matches_df() -> pd.DataFrame:
    with db_session() as session:
        rows = session.query(Match).order_by(Match.created_at.desc()).all()
        names = {p.user_id: (p.pseudo or str(p.user_id))
                 for p in session.query(Profile).all()}
        data = [{
            "ID": m.id,
            "Homme": names.get(m.user_m_id, m.user_m_id),
            "Femme": names.get(m.user_f_id, m.user_f_id),
            "Score": m.score,
            "Réponse (H)": m.response_m,
            "Réponse (F)": m.response_f,
            "Statut": m.status,
            "Créé le": m.created_at,
            "Détails": m.details,
        } for m in rows]
    return pd.DataFrame(data)


STATUS_LABELS = {"proposed": "proposé", "mutual": "accepté (mutuel)",
                 "refused": "refusé", "expired": "expiré"}

st.title("🌙 Tableau de bord administrateur")
tab_stats, tab_users, tab_matches, tab_convs = st.tabs(
    ["📊 Statistiques", "👥 Utilisateurs", "💫 Matchs", "💬 Conversations"])


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------
with tab_stats:
    users_df = load_users_df()
    matches_df = load_matches_df()
    week_ago = utcnow() - dt.timedelta(days=7)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Utilisateurs", len(users_df))
    hommes = int((users_df["Sexe"] == "homme").sum()) if len(users_df) else 0
    femmes = int((users_df["Sexe"] == "femme").sum()) if len(users_df) else 0
    c2.metric("Hommes / Femmes", f"{hommes} / {femmes}")
    actifs = int((users_df["Actif"] == "oui").sum()) if len(users_df) else 0
    c3.metric("Profils actifs", actifs)
    if len(users_df):
        incomplets = int((users_df["Complétude (%)"] < 50).sum())
    else:
        incomplets = 0
    c4.metric("Profils incomplets (<50%)", incomplets)

    c5, c6, c7, c8 = st.columns(4)
    nouveaux = int((users_df["Inscription"] >= week_ago).sum()) if len(users_df) else 0
    c5.metric("Nouveaux (7 j)", nouveaux)
    c6.metric("Matchs générés", len(matches_df))
    if len(matches_df):
        responded = matches_df[matches_df["Statut"].isin(["mutual", "refused"])]
        acceptes = int((matches_df["Statut"] == "mutual").sum())
        taux = f"{acceptes / len(responded) * 100:.0f}%" if len(responded) else "—"
    else:
        acceptes, taux = 0, "—"
    c7.metric("Matchs mutuels", acceptes)
    c8.metric("Taux d'acceptation", taux)

    if len(users_df):
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Complétude des profils")
            bins = pd.cut(users_df["Complétude (%)"],
                          bins=[0, 20, 40, 60, 80, 100],
                          labels=["0-20", "20-40", "40-60", "60-80", "80-100"],
                          include_lowest=True)
            st.bar_chart(bins.value_counts().sort_index())
        with col_b:
            st.subheader("Inscriptions par semaine")
            insc = users_df.copy()
            insc["Semaine"] = pd.to_datetime(insc["Inscription"]).dt.to_period("W").astype(str)
            st.bar_chart(insc.groupby("Semaine").size())


# ---------------------------------------------------------------------------
# Utilisateurs : recherche avancée + fiche détaillée
# ---------------------------------------------------------------------------
with tab_users:
    users_df = load_users_df()
    if users_df.empty:
        st.info("Aucun utilisateur pour le moment.")
    else:
        with st.expander("🔍 Recherche avancée", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            search = f1.text_input("Recherche (nom, pseudo, ID)")
            sexe = f2.selectbox("Sexe", ["Tous", "homme", "femme"])
            situation = f3.selectbox("Situation familiale",
                                     ["Toutes", "celibataire", "divorce", "veuf"])
            statut = f4.selectbox("Statut du profil", ["Tous", "actif", "inactif"])
            f5, f6, f7, f8 = st.columns(4)
            ville = f5.text_input("Ville")
            departement = f6.text_input("Département")
            pays = f7.text_input("Pays")
            profession = f8.text_input("Profession")
            ages = st.slider("Tranche d'âge", 18, 70, (18, 70))
            completude = st.slider("Complétude minimale (%)", 0, 100, 0)

        df = users_df
        if search:
            s = search.lower()
            df = df[df.apply(lambda r: s in str(r["Prénom"]).lower()
                             or s in str(r["Pseudo Telegram"]).lower()
                             or s in str(r["ID Telegram"]), axis=1)]
        if sexe != "Tous":
            df = df[df["Sexe"] == sexe]
        if situation != "Toutes":
            df = df[df["Situation"] == situation]
        if statut != "Tous":
            df = df[df["Actif"] == ("oui" if statut == "actif" else "non")]
        for col, val in [("Ville", ville), ("Département", departement),
                         ("Pays", pays), ("Profession", profession)]:
            if val:
                df = df[df[col].fillna("").str.contains(val, case=False)]
        df = df[(df["Âge"].fillna(0).between(*ages)) | df["Âge"].isna()]
        df = df[df["Complétude (%)"] >= completude]

        st.caption(f"{len(df)} profil(s) trouvé(s)")
        st.dataframe(df.drop(columns=["Pratique religieuse"]),
                     width="stretch", hide_index=True)

        st.divider()
        st.subheader("Fiche détaillée")
        if len(df):
            options = {f"{r['Prénom'] or '—'} (ID {r['ID Telegram']})": r["ID Telegram"]
                       for _, r in df.iterrows()}
            choice = st.selectbox("Choisir un utilisateur", list(options))
            uid = options[choice]
            with db_session() as session:
                user = session.get(User, uid)
                p = user.profile
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
**Identifiant Telegram :** `{user.telegram_id}` — @{user.username or '—'}
**Prénom :** {p.pseudo or '—'}  |  **Sexe :** {p.gender or '—'}  |  **Âge :** {p.age or '—'}
**Naissance :** {p.birth_date or '—'} à {p.birth_place or '—'}
**Ville :** {p.city or '—'} ({p.department or '—'}, {p.country or '—'})
**Profession :** {p.profession or '—'}  |  **Études :** {p.education or '—'}
**Situation :** {p.marital_status or '—'}
**Inscription :** {user.created_at:%d/%m/%Y}  |  **Dernière activité :** {user.last_active_at:%d/%m/%Y %H:%M}
""")
                with col2:
                    st.markdown(f"""
**Projet :** mariage {p.marriage_timeline or '(délai non précisé)'} —
enfants : { {True: 'oui', False: 'non'}.get(p.wants_children, '—') }
({p.children_count_desired or '—'} souhaités)
**Pratique religieuse :** {p.religious_practice or '—'}
**Mosquée :** {p.mosque_attendance or '—'}
**Apprentissage :** {p.religious_education or '—'}
**Personnalité :** {', '.join(p.personality_traits or []) or '—'}
**Centres d'intérêt :** {', '.join(p.interests or []) or '—'}
**Habitudes de vie :** {', '.join(p.lifestyle_facts or []) or '—'}
""")
                st.progress(p.completeness / 100,
                            text=f"Indice de connaissance du profil : {p.completeness}/100")
                if p.memory_notes:
                    st.markdown("**Notes mémorisées par le bot :**")
                    for note in p.memory_notes:
                        st.markdown(f"- {note}")


# ---------------------------------------------------------------------------
# Matchs
# ---------------------------------------------------------------------------
with tab_matches:
    matches_df = load_matches_df()
    if matches_df.empty:
        st.info("Aucun match pour le moment.")
    else:
        filtre = st.multiselect("Statut", list(STATUS_LABELS.values()),
                                default=list(STATUS_LABELS.values()))
        inv = {v: k for k, v in STATUS_LABELS.items()}
        keep = [inv[v] for v in filtre]
        df = matches_df[matches_df["Statut"].isin(keep)].copy()
        df["Statut"] = df["Statut"].map(STATUS_LABELS)
        st.dataframe(df.drop(columns=["Détails"]),
                     width="stretch", hide_index=True)

        st.subheader("Décomposition d'un score")
        if len(df):
            mid = st.selectbox("Match", df["ID"].tolist())
            details = matches_df.loc[matches_df["ID"] == mid, "Détails"].iloc[0]
            if details:
                st.bar_chart(pd.Series(details))


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
with tab_convs:
    st.caption("⚠️ Accès réservé à la modération, dans le respect du RGPD : "
               "consultez uniquement en cas de nécessité (signalement, sécurité).")
    users_df = load_users_df()
    if users_df.empty:
        st.info("Aucune conversation.")
    else:
        options = {f"{r['Prénom'] or '—'} (ID {r['ID Telegram']})": r["ID Telegram"]
                   for _, r in users_df.iterrows()}
        choice = st.selectbox("Utilisateur", list(options), key="conv_user")
        uid = options[choice]
        with db_session() as session:
            msgs = (session.query(Message).filter(Message.user_id == uid)
                    .order_by(Message.created_at.asc()).all())
            topics = [q.topic for q in session.query(AskedQuestion)
                      .filter(AskedQuestion.user_id == uid).all()]
        if topics:
            st.caption("Sujets déjà abordés par le bot : " + ", ".join(topics))
        if not msgs:
            st.info("Aucun message échangé avec cet utilisateur.")
        for m in msgs:
            with st.chat_message("user" if m.role == "user" else "assistant"):
                st.markdown(m.content)
                st.caption(f"{m.created_at:%d/%m/%Y %H:%M}")
