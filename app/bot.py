"""Bot Telegram : conversations privées, suggestions de match et animation
communautaire.

Lancement :  python -m app.bot
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import random

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update)
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

from . import admin_commands, ai, config, matching
from .db import (CommunityPost, Match, Message, Profile, User, db_session,
                 get_or_create_user, utcnow)
from .profile_schema import FIELD_LABELS

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("bot")

WELCOME = (
    "Assalamou alaykoum et bienvenue ! 🌙\n\n"
    "Je suis l'assistant de cette communauté de rencontre entre musulmans et "
    "musulmanes en vue du mariage. Nous allons faire connaissance petit à petit, "
    "au fil de conversations simples — pas de long questionnaire à remplir.\n\n"
    "Plus j'apprends à te connaître, plus je pourrai te proposer des profils "
    "réellement compatibles. Tu peux consulter ton profil à tout moment avec /profil.\n\n"
    "Pour commencer : comment souhaites-tu que je t'appelle ?"
)

AI_ERROR_REPLY = ("Désolé, j'ai un petit souci technique. "
                  "Réessaie dans quelques instants, barakAllahou fik.")


# ---------------------------------------------------------------------------
# Commandes
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    with db_session() as session:
        user = get_or_create_user(session, tg_user.id, tg_user.username, tg_user.full_name)
        session.add(Message(user_id=user.telegram_id, role="assistant", content=WELCOME))
        # Le message d'accueil demande le prénom : en mode guidé (sans API),
        # on le mémorise pour que la première réponse soit comprise comme tel.
        if not ai.ai_enabled():
            from .db import AskedQuestion
            already = (session.query(AskedQuestion)
                       .filter(AskedQuestion.user_id == user.telegram_id,
                               AskedQuestion.topic == "pseudo").count())
            if not already:
                session.add(AskedQuestion(user_id=user.telegram_id, topic="pseudo"))
    await update.message.reply_text(WELCOME)


async def cmd_profil(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with db_session() as session:
        user = get_or_create_user(session, update.effective_user.id)
        p = user.profile
        lines = [f"📋 *Ton profil* — indice de connaissance : *{p.completeness}/100*\n"]
        rows = [
            ("Prénom/pseudo", p.pseudo), ("Sexe", p.gender), ("Âge", p.age),
            ("Ville", p.city), ("Pays", p.country), ("Profession", p.profession),
            ("Études", p.education), ("Situation", p.marital_status),
            ("Délai mariage", p.marriage_timeline),
            ("Souhaite des enfants", {True: "oui", False: "non"}.get(p.wants_children)),
            ("Pratique religieuse", p.religious_practice),
            ("Personnalité", ", ".join(p.personality_traits or []) or None),
            ("Centres d'intérêt", ", ".join(p.interests or []) or None),
        ]
        for label, value in rows:
            lines.append(f"• {label} : {value if value not in (None, '') else '_à découvrir_'}")
        lines.append("\nContinue nos conversations pour enrichir ton profil ✨")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_aide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤝 *Comment ça marche ?*\n\n"
        "• Discute simplement avec moi : j'apprends à te connaître au fil des échanges.\n"
        "• Quand un profil compatible est identifié, je te préviens et tu choisis : "
        "en savoir plus, accepter, refuser ou reporter.\n"
        "• /profil — voir ton profil et son niveau de complétude\n"
        "• /pause — suspendre les suggestions\n"
        "• /reprendre — réactiver les suggestions",
        parse_mode=ParseMode.MARKDOWN)


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with db_session() as session:
        user = get_or_create_user(session, update.effective_user.id)
        user.is_active = False
    await update.message.reply_text("Suggestions suspendues. Reviens quand tu veux avec /reprendre 🤲")


async def cmd_reprendre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with db_session() as session:
        user = get_or_create_user(session, update.effective_user.id)
        user.is_active = True
    await update.message.reply_text("Heureux de te revoir ! Les suggestions sont réactivées ✨")


# ---------------------------------------------------------------------------
# Conversation libre -> IA
# ---------------------------------------------------------------------------
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return  # l'IA ne répond qu'en privé
    tg_user = update.effective_user
    text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                       action=ChatAction.TYPING)

    def _turn() -> str:
        with db_session() as session:
            user = get_or_create_user(session, tg_user.id, tg_user.username, tg_user.full_name)
            return ai.handle_user_message(session, user, text)

    try:
        reply = await asyncio.to_thread(_turn)
    except Exception:
        log.exception("Échec du tour de conversation pour %s", tg_user.id)
        reply = AI_ERROR_REPLY
    await update.message.reply_text(reply)


# ---------------------------------------------------------------------------
# Suggestions de match
# ---------------------------------------------------------------------------
def _match_card(profile: Profile, score: float) -> str:
    interests = ", ".join((profile.interests or [])[:4])
    traits = ", ".join((profile.personality_traits or [])[:4])
    return (
        "💫 *Nous avons identifié un profil susceptible de correspondre à tes attentes.*\n\n"
        f"• Âge : {profile.age or '—'} ans\n"
        f"• Ville : {profile.city or '—'} ({profile.country or '—'})\n"
        f"• Profession : {profile.profession or '—'}\n"
        f"• Situation : {profile.marital_status or '—'}\n"
        f"• Personnalité : {traits or '—'}\n"
        f"• Centres d'intérêt : {interests or '—'}\n\n"
        f"Compatibilité estimée : *{round(score)}%*\n"
        "Que souhaites-tu faire ?"
    )


def _match_keyboard(match_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ℹ️ Plus d'infos", callback_data=f"match:{match_id}:info"),
         InlineKeyboardButton("✅ Accepter", callback_data=f"match:{match_id}:accepted")],
        [InlineKeyboardButton("❌ Refuser", callback_data=f"match:{match_id}:refused"),
         InlineKeyboardButton("🕐 Plus tard", callback_data=f"match:{match_id}:postponed")],
    ])


async def job_matching(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job périodique : calcule les nouveaux matchs et envoie les suggestions."""
    def _compute():
        with db_session() as session:
            created = matching.find_new_matches(session)
            payload = []
            for m in created:
                pm = session.get(Profile, m.user_m_id)
                pf = session.get(Profile, m.user_f_id)
                payload.append((m.id, m.user_m_id, m.user_f_id, m.score, pm, pf))
            return payload

    try:
        new_matches = await asyncio.to_thread(_compute)
    except Exception:
        log.exception("Échec du calcul des matchs")
        return

    for match_id, m_id, f_id, score, pm, pf in new_matches:
        for recipient, other in [(m_id, pf), (f_id, pm)]:
            try:
                await context.bot.send_message(
                    chat_id=recipient, text=_match_card(other, score),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=_match_keyboard(match_id))
            except TelegramError:
                log.warning("Impossible d'envoyer la suggestion %s à %s", match_id, recipient)
    if new_matches:
        log.info("%d nouvelle(s) suggestion(s) envoyée(s)", len(new_matches))


async def on_match_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        _, match_id_s, response = query.data.split(":")
        match_id = int(match_id_s)
    except ValueError:
        return
    responder_id = query.from_user.id

    def _apply():
        with db_session() as session:
            match = session.get(Match, match_id)
            if match is None:
                return None, None, None
            if response != "info":
                matching.register_response(session, match, responder_id, response)
            other_id = match.user_f_id if responder_id == match.user_m_id else match.user_m_id
            other_profile = session.get(Profile, other_id)
            other_user = session.get(User, other_id)
            return match, other_profile, other_user

    match, other_profile, other_user = await asyncio.to_thread(_apply)
    if match is None:
        await query.edit_message_reply_markup(None)
        return

    if response == "info":
        p = other_profile
        await query.message.reply_text(
            "ℹ️ *En savoir plus*\n\n"
            f"• Études : {p.education or '—'}\n"
            f"• Délai souhaité pour le mariage : {p.marriage_timeline or '—'}\n"
            f"• Souhaite des enfants : "
            f"{ {True: 'oui', False: 'non'}.get(p.wants_children, '—') }\n"
            f"• Pratique religieuse : {p.religious_practice or '—'}\n"
            f"• Habitudes de vie : {', '.join((p.lifestyle_facts or [])[:4]) or '—'}",
            parse_mode=ParseMode.MARKDOWN)
        return

    confirmations = {
        "accepted": "✅ C'est noté ! Si l'autre personne accepte aussi, je vous mets en relation, in shâ Allah.",
        "refused": "❌ C'est noté, merci pour ta franchise. Je continue mes recherches pour toi.",
        "postponed": "🕐 Très bien, je te reproposerai ce profil plus tard.",
    }
    await query.edit_message_reply_markup(None)
    await query.message.reply_text(confirmations.get(response, "C'est noté."))

    # Mise en relation mutuelle
    if match.status == "mutual":
        for uid, other in [(match.user_m_id, match.user_f_id), (match.user_f_id, match.user_m_id)]:
            def _contact(oid=other):
                with db_session() as session:
                    u = session.get(User, oid)
                    p = session.get(Profile, oid)
                    handle = f"@{u.username}" if u and u.username else "(pseudo Telegram non renseigné)"
                    return p.pseudo or "ce membre", handle
            pseudo, handle = await asyncio.to_thread(_contact)
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=f"🎉 *Excellente nouvelle !* Vous avez tous les deux accepté la mise en relation.\n\n"
                         f"Tu peux maintenant contacter {pseudo} : {handle}\n\n"
                         "Nous vous souhaitons un échange sincère et respectueux. "
                         "Qu'Allah vous facilite. 🤲",
                    parse_mode=ParseMode.MARKDOWN)
            except TelegramError:
                log.warning("Notification de match mutuel impossible pour %s", uid)


# ---------------------------------------------------------------------------
# Relance : enrichissement progressif des profils incomplets
# ---------------------------------------------------------------------------
RELAUNCH_AFTER_HOURS = 48

async def job_enrichment(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Relance en douceur les membres inactifs dont le profil est incomplet.
    Le bot choisit sa question via l'IA, en priorisant les profils les moins connus."""
    def _candidates():
        cutoff = utcnow() - dt.timedelta(hours=RELAUNCH_AFTER_HOURS)
        with db_session() as session:
            users = (session.query(User)
                     .join(Profile)
                     .filter(User.is_active.is_(True),
                             User.last_active_at < cutoff,
                             Profile.completeness < 80)
                     .order_by(Profile.completeness.asc())
                     .limit(10).all())
            return [u.telegram_id for u in users]

    try:
        ids = await asyncio.to_thread(_candidates)
    except Exception:
        log.exception("Échec de la sélection des profils à relancer")
        return

    for uid in ids:
        def _turn(uid=uid):
            with db_session() as session:
                user = session.get(User, uid)
                return ai.handle_user_message(
                    session, user,
                    "[relance automatique : reprends contact chaleureusement et pose une "
                    "nouvelle question pour mieux me connaître]")
        try:
            reply = await asyncio.to_thread(_turn)
            await context.bot.send_message(chat_id=uid, text=reply)
        except Exception:
            log.warning("Relance impossible pour %s", uid)


# ---------------------------------------------------------------------------
# Animation communautaire (si COMMUNITY_CHAT_ID est configuré)
# ---------------------------------------------------------------------------
POLL_BANK = [
    ("Quel critère compte le plus pour vous dans le choix d'un(e) époux(se) ?",
     ["La pratique religieuse", "Le caractère", "La situation stable", "La famille"]),
    ("Où rêveriez-vous de vivre après le mariage ?",
     ["Dans mon pays actuel", "Dans un pays musulman", "Peu importe, avec la bonne personne", "Près de ma famille"]),
    ("Le meilleur moment pour se marier, c'est…",
     ["Dès que possible", "Après les études", "Une fois stable financièrement", "Quand on trouve la bonne personne"]),
]


async def job_community(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Publie chaque jour un contenu différent dans le groupe communautaire."""
    if not config.COMMUNITY_CHAT_ID:
        return
    chat_id = int(config.COMMUNITY_CHAT_ID)
    weekday = dt.date.today().weekday()
    # Rotation hebdomadaire : lun=question, mar=sondage, mer=quiz, jeu=stats,
    # ven=profil de la semaine, sam=rappel des règles, dim=question
    kinds = ["question", "sondage", "quiz", "stats", "profil_semaine", "regles", "question"]
    kind = kinds[weekday]

    try:
        if kind == "sondage":
            question, options = random.choice(POLL_BANK)
            await context.bot.send_poll(chat_id=chat_id, question=question,
                                        options=options, is_anonymous=True)
            content = question
        elif kind == "stats":
            content = await asyncio.to_thread(_stats_text)
            await context.bot.send_message(chat_id=chat_id, text=content)
        elif kind == "profil_semaine":
            content = await asyncio.to_thread(_profile_of_week_text)
            if not content:
                return
            await context.bot.send_message(chat_id=chat_id, text=content,
                                           parse_mode=ParseMode.MARKDOWN)
        elif kind == "regles":
            content = await asyncio.to_thread(ai.generate_community_text, "rappel_regles")
            await context.bot.send_message(chat_id=chat_id, text="📜 Petit rappel :\n\n" + content)
        else:  # question / quiz générés par l'IA
            ai_kind = "quiz" if kind == "quiz" else "question"
            content = await asyncio.to_thread(ai.generate_community_text, ai_kind)
            prefix = "🧠 Quiz du jour !\n\n" if ai_kind == "quiz" else "💭 Question du jour :\n\n"
            await context.bot.send_message(chat_id=chat_id, text=prefix + content)

        def _log_post():
            with db_session() as session:
                session.add(CommunityPost(kind=kind, content=content))
        await asyncio.to_thread(_log_post)
    except Exception:
        log.exception("Échec de la publication communautaire (%s)", kind)


def _stats_text() -> str:
    with db_session() as session:
        week_ago = utcnow() - dt.timedelta(days=7)
        total = session.query(User).count()
        new = session.query(User).filter(User.created_at >= week_ago).count()
        matches = session.query(Match).filter(Match.created_at >= week_ago).count()
        mutual = session.query(Match).filter(Match.status == "mutual",
                                             Match.updated_at >= week_ago).count()
    return ("📊 Cette semaine dans la communauté :\n"
            f"• {new} nouveau(x) membre(s) — {total} au total\n"
            f"• {matches} nouvelle(s) mise(s) en relation proposée(s)\n"
            f"• {mutual} match(s) mutuel(s) 🎉\n\n"
            "Qu'Allah facilite à chacun d'entre vous !")


def _profile_of_week_text() -> str | None:
    """Portrait anonymisé d'un membre au profil bien rempli."""
    with db_session() as session:
        p = (session.query(Profile).join(User)
             .filter(User.is_active.is_(True), Profile.completeness >= 50)
             .order_by(Profile.updated_at.desc()).first())
        if p is None:
            return None
        genre = "Frère" if p.gender == "homme" else "Sœur"
        return (f"🌟 *Profil de la semaine* (anonyme)\n\n"
                f"{genre}, {p.age or '—'} ans, vit en {p.country or '—'}.\n"
                f"Profession : {p.profession or '—'}.\n"
                f"Personnalité : {', '.join((p.personality_traits or [])[:3]) or '—'}.\n"
                f"Aime : {', '.join((p.interests or [])[:3]) or '—'}.\n\n"
                "Intéressé(e) ? Parle-m'en en message privé 😉")


# ---------------------------------------------------------------------------
def build_application() -> Application:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN manquant : copiez .env.example vers .env "
                         "et renseignez le jeton du bot.")
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("profil", cmd_profil))
    app.add_handler(CommandHandler("aide", cmd_aide))
    app.add_handler(CommandHandler("help", cmd_aide))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("reprendre", cmd_reprendre))
    app.add_handler(CallbackQueryHandler(on_match_button, pattern=r"^match:"))
    admin_commands.register(app)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    jq = app.job_queue
    jq.run_repeating(job_matching, interval=dt.timedelta(hours=6), first=60)
    jq.run_repeating(job_enrichment, interval=dt.timedelta(hours=24), first=120)
    jq.run_daily(job_community, time=dt.time(hour=18, minute=0))
    return app


def main() -> None:
    app = build_application()
    log.info("Bot démarré — en attente de messages…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
