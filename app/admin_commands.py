"""Administration par Telegram : gérez la plateforme depuis votre smartphone.

Les commandes sont réservées aux IDs listés dans ADMIN_TELEGRAM_IDS (.env).
Obtenez votre ID avec /monid, ajoutez-le au .env, redémarrez le bot.
"""
from __future__ import annotations

import datetime as dt
import functools
import json
import logging
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from . import ai, config
from .db import (AskedQuestion, Match, Message, Preference, Profile, Report,
                 User, db_session, utcnow)

log = logging.getLogger("admin")

HELP_TEXT = (
    "🛠 *Commandes administrateur*\n\n"
    "• /admin — statistiques générales\n"
    "• /membres `[recherche]` — derniers membres (ou recherche)\n"
    "• /fiche `<id>` — fiche complète d'un membre\n"
    "• /matchs — derniers matchs et scores\n"
    "• /conv `<id>` — derniers échanges bot ↔ membre\n"
    "• /journal `[n]` — comportement du modèle (n derniers tours)\n"
    "• /signalements — signalements en attente de modération\n"
    "• /publier `question|quiz|regles|stats` — publier dans le groupe\n"
)


def admin_only(handler):
    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid not in config.ADMIN_TELEGRAM_IDS:
            if not config.ADMIN_TELEGRAM_IDS:
                await update.message.reply_text(
                    "Aucun administrateur configuré. Ajoutez votre ID "
                    f"({uid}) à ADMIN_TELEGRAM_IDS dans le .env puis redémarrez le bot.")
            # sinon : silence pour ne pas révéler l'existence des commandes
            return
        await handler(update, context)
    return wrapper


async def cmd_monid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Public : renvoie l'ID Telegram (nécessaire pour se déclarer admin)."""
    await update.message.reply_text(
        f"Ton identifiant Telegram est : `{update.effective_user.id}`",
        parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with db_session() as s:
        week_ago = utcnow() - dt.timedelta(days=7)
        total = s.query(User).count()
        men = s.query(Profile).filter(Profile.gender == "homme").count()
        women = s.query(Profile).filter(Profile.gender == "femme").count()
        active = s.query(User).filter(User.is_active.is_(True)).count()
        incomplete = s.query(Profile).filter(Profile.completeness < 50).count()
        new7 = s.query(User).filter(User.created_at >= week_ago).count()
        matches = s.query(Match).count()
        mutual = s.query(Match).filter(Match.status == "mutual").count()
        refused = s.query(Match).filter(Match.status == "refused").count()
    responded = mutual + refused
    rate = f"{mutual / responded * 100:.0f}%" if responded else "—"
    await update.message.reply_text(
        "📊 *Vue d'ensemble*\n\n"
        f"• Membres : *{total}* ({men} H / {women} F) — {active} actifs\n"
        f"• Profils incomplets (<50%) : {incomplete}\n"
        f"• Nouveaux (7 j) : {new7}\n"
        f"• Matchs : *{matches}* — {mutual} mutuels, {refused} refusés\n"
        f"• Taux d'acceptation : {rate}\n\n" + HELP_TEXT,
        parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_membres(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    search = " ".join(context.args).lower() if context.args else ""
    with db_session() as s:
        rows = (s.query(User, Profile)
                .join(Profile, Profile.user_id == User.telegram_id)
                .order_by(User.created_at.desc()).all())
        lines = []
        for user, p in rows:
            hay = " ".join(filter(None, [p.pseudo, user.username, p.city,
                                         str(user.telegram_id)])).lower()
            if search and search not in hay:
                continue
            genre = {"homme": "H", "femme": "F"}.get(p.gender, "?")
            lines.append(f"• *{p.pseudo or user.display_name or '—'}* ({genre}, "
                         f"{p.age or '?'} ans, {p.city or '?'}) — "
                         f"{p.completeness}% — `/fiche {user.telegram_id}`")
            if len(lines) >= 15:
                break
    title = f"👥 *Membres* ({'recherche : ' + search if search else 'les 15 derniers'})\n\n"
    await update.message.reply_text(
        title + ("\n".join(lines) if lines else "Aucun membre trouvé."),
        parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_fiche(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.message.reply_text("Utilisation : /fiche <id>  (voir /membres)")
        return
    uid = int(context.args[0])
    with db_session() as s:
        user = s.get(User, uid)
        if user is None:
            await update.message.reply_text("Membre introuvable.")
            return
        p = user.profile
        oui_non = {True: "oui", False: "non"}
        prefs = (s.query(Preference).filter(Preference.user_id == uid)
                 .order_by(Preference.confidence.desc()).limit(8).all())
        prefs_txt = "\n".join(
            f"  – [{pr.dimension}] {pr.key} : {pr.orientation} "
            f"({pr.confidence}%, {pr.occurrences} obs.)" for pr in prefs) or "  – aucune pour le moment"
        await update.message.reply_text(
            f"📋 *{p.pseudo or user.display_name or '—'}* — `{uid}` "
            f"(@{user.username or '—'})\n"
            f"Indice de connaissance : *{p.completeness}/100*\n\n"
            f"• {p.gender or '—'}, {p.age or '—'} ans, {p.marital_status or '—'}\n"
            f"• Né(e) le {p.birth_date or '—'} à {p.birth_place or '—'}\n"
            f"• Vit à {p.city or '—'} ({p.department or '—'}, {p.country or '—'})\n"
            f"• {p.profession or '—'} — études : {p.education or '—'}\n"
            f"• Mariage : {p.marriage_timeline or '—'} — enfants : "
            f"{oui_non.get(p.wants_children, '—')} ({p.children_count_desired or '—'})\n"
            f"• Pratique : {p.religious_practice or '—'}\n"
            f"• Mosquée : {p.mosque_attendance or '—'} — "
            f"apprentissage : {p.religious_education or '—'}\n"
            f"• Personnalité : {', '.join(p.personality_traits or []) or '—'}\n"
            f"• Intérêts : {', '.join(p.interests or []) or '—'}\n"
            f"• Habitudes : {', '.join(p.lifestyle_facts or []) or '—'}\n"
            f"• Notes du bot : {' · '.join(p.memory_notes or []) or '—'}\n"
            f"• Préférences apprises (réactions) :\n{prefs_txt}\n\n"
            f"Inscrit le {user.created_at:%d/%m/%Y} — dernière activité "
            f"{user.last_active_at:%d/%m/%Y %H:%M}\n"
            f"Conversation : `/conv {uid}`",
            parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_matchs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    labels = {"proposed": "⏳ proposé", "mutual": "🎉 mutuel",
              "refused": "❌ refusé", "expired": "expiré"}
    with db_session() as s:
        names = {p.user_id: (p.pseudo or str(p.user_id)) for p in s.query(Profile).all()}
        rows = s.query(Match).order_by(Match.created_at.desc()).limit(10).all()
        lines = [f"• *{names.get(m.user_m_id)}* ↔ *{names.get(m.user_f_id)}* — "
                 f"score {m.score} — {labels.get(m.status, m.status)} "
                 f"(H: {m.response_m}, F: {m.response_f})"
                 for m in rows]
    await update.message.reply_text(
        "💫 *Derniers matchs*\n\n" + ("\n".join(lines) if lines else "Aucun match."),
        parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.message.reply_text("Utilisation : /conv <id>")
        return
    uid = int(context.args[0])
    with db_session() as s:
        msgs = (s.query(Message).filter(Message.user_id == uid)
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(10).all())
    if not msgs:
        await update.message.reply_text("Aucun message pour ce membre.")
        return
    lines = []
    for m in reversed(msgs):
        who = "👤" if m.role == "user" else "🤖"
        content = m.content if len(m.content) <= 300 else m.content[:300] + "…"
        lines.append(f"{who} {content}")
    await update.message.reply_text(
        f"💬 10 derniers échanges avec `{uid}`\n(accès modération — RGPD)\n\n"
        + "\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_journal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Résumé des derniers tours (comportement du modèle) depuis le journal."""
    n = 5
    if context.args and context.args[0].isdigit():
        n = min(int(context.args[0]), 15)
    path = Path(config.CONV_LOG_PATH)
    if not path.exists():
        await update.message.reply_text("Journal vide pour l'instant (aucun échange enregistré).")
        return
    lines = path.read_text(encoding="utf-8").strip().splitlines()[-n:]
    if not lines:
        await update.message.reply_text("Journal vide.")
        return
    blocks = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except Exception:
            continue
        flag = "⚠️repli" if r.get("fallback") else "✓"
        sigs = ", ".join(f"{s.get('cle')}({s.get('orientation','')[:3]})"
                         for s in r.get("preference_signals", [])) or "—"
        upd = ", ".join(f"{k}={v}" for k, v in (r.get("updates") or {}).items()) or "—"
        um = (r.get("user_message") or "")[:120]
        rep = (r.get("reply") or "")[:160]
        blocks.append(
            f"🕐 {r.get('ts','')[-8:]} · {r.get('duration_s','?')}s · {flag}\n"
            f"👤 {um}\n🤖 {rep}\n"
            f"📊 infos: {upd}\n🧭 préf.: {sigs}")
    await update.message.reply_text(
        f"📓 *{len(blocks)} derniers tours* (modèle : {config.MLX_MODEL if ai.llm.provider()=='mlx' else ai.llm.provider()})\n\n"
        + "\n\n".join(blocks), parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_signalements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with db_session() as s:
        names = {p.user_id: (p.pseudo or str(p.user_id)) for p in s.query(Profile).all()}
        rows = (s.query(Report).filter(Report.status == "open")
                .order_by(Report.created_at.desc()).limit(15).all())
        lines = []
        for r in rows:
            cible = names.get(r.reported_id, r.reported_id) if r.reported_id else "(général)"
            lines.append(f"• #{r.id} — {names.get(r.reporter_id, r.reporter_id)} → "
                         f"*{cible}* ({r.created_at:%d/%m %H:%M})\n"
                         f"  {r.reason or '—'}\n"
                         f"  fiche cible : `/fiche {r.reported_id}`" if r.reported_id else
                         f"• #{r.id} — {names.get(r.reporter_id, r.reporter_id)} : {r.reason or '—'}")
    await update.message.reply_text(
        "🚩 *Signalements ouverts*\n\n" + ("\n\n".join(lines) if lines
        else "Aucun signalement en attente. ✅"), parse_mode=ParseMode.MARKDOWN)


@admin_only
async def cmd_publier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not config.COMMUNITY_CHAT_ID:
        await update.message.reply_text(
            "COMMUNITY_CHAT_ID n'est pas configuré dans le .env — ajoutez l'ID "
            "de votre groupe pour publier.")
        return
    kind = context.args[0].lower() if context.args else "question"
    if kind not in ("question", "quiz", "regles", "stats"):
        await update.message.reply_text("Utilisation : /publier question|quiz|regles|stats")
        return
    from .bot import _stats_text  # import local pour éviter le cycle
    import asyncio
    if kind == "stats":
        content = await asyncio.to_thread(_stats_text)
    else:
        ai_kind = {"regles": "rappel_regles"}.get(kind, kind)
        content = await asyncio.to_thread(ai.generate_community_text, ai_kind)
        prefix = {"question": "💭 Question du jour :\n\n",
                  "quiz": "🧠 Quiz !\n\n", "regles": "📜 Petit rappel :\n\n"}[kind]
        content = prefix + content
    await context.bot.send_message(chat_id=int(config.COMMUNITY_CHAT_ID), text=content)
    await update.message.reply_text("✅ Publié dans le groupe.")


def register(app) -> None:
    app.add_handler(CommandHandler("monid", cmd_monid))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("membres", cmd_membres))
    app.add_handler(CommandHandler("fiche", cmd_fiche))
    app.add_handler(CommandHandler("matchs", cmd_matchs))
    app.add_handler(CommandHandler("conv", cmd_conv))
    app.add_handler(CommandHandler("journal", cmd_journal))
    app.add_handler(CommandHandler("signalements", cmd_signalements))
    app.add_handler(CommandHandler("publier", cmd_publier))
