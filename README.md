# 🌙 Plateforme de mise en relation entre musulmans — Bot Telegram + Dashboard admin

Plateforme de rencontre sérieuse (en vue du mariage) utilisant **Telegram** comme
interface principale. Le bot construit un **profil riche** de chaque membre à
travers des **conversations naturelles** (propulsées par l'API Claude), propose
des profils compatibles grâce à un **moteur de matching**, anime la communauté,
et fournit à l'administrateur un **tableau de bord web local** (FastAPI, aucun
service externe requis).

## Fonctionnalités

### 🤖 Bot Telegram (`app/bot.py`)
- **Collecte intelligente et progressive** : pas de long questionnaire — le bot
  pose une question à la fois, rebondit sur les réponses ("Tu aimes voyager ?
  Quel pays t'a le plus marqué ?") et enrichit le profil au fil des jours.
- **Mémoire conversationnelle** : historique persistant, sujets déjà abordés
  jamais reposés, notes mémorisées ré-utilisées dans les échanges suivants.
- **Indice de connaissance du profil (0-100)** : calculé en continu ; le bot
  cible en priorité les informations manquantes et relance en douceur les
  profils incomplets (job automatique).
- **Suggestions de match** : quand un score dépasse le seuil, chaque membre
  reçoit une carte anonymisée avec boutons *Plus d'infos / Accepter / Refuser /
  Plus tard*. En cas d'accord mutuel, mise en relation automatique.
- **Animation communautaire** (si `COMMUNITY_CHAT_ID` est défini) : rotation
  quotidienne — question de réflexion, sondage, quiz, statistiques anonymisées,
  profil de la semaine, rappel des règles.
- Commandes : `/start`, `/profil`, `/aide`, `/pause`, `/reprendre`.

### 🪶 Mode sans API (démarrage à coût zéro)
Si `ANTHROPIC_API_KEY` est **vide**, le bot bascule automatiquement en
**questionnaire guidé** (`app/scripted.py`) : questions prédéfinies posées une
à la fois, analyse des réponses par règles (dates, âges, oui/non, listes...),
contenus communautaires issus d'une banque statique. Le profil, l'indice de
connaissance, le matching et le dashboard fonctionnent à l'identique.
Ajoutez la clé plus tard dans `.env` et redémarrez : le bot passe en
conversations naturelles, sans aucune autre modification.

### 💘 Moteur de matching (`app/matching.py`)
- **Obligatoires** (éliminatoires) : sexes opposés, majorité, tranche d'âge,
  complétude minimale des deux profils.
- **Importantes** (70 pts) : pratique religieuse, projet de famille,
  localisation, personnalité.
- **Secondaires** (30 pts) : centres d'intérêt, habitudes de vie, proximité d'âge.
- Chaque paire reçoit un **score 0-100** avec décomposition consultable dans le
  dashboard.

### 📱 Administration par smartphone (`app/admin_commands.py`)
Gérez toute la plateforme **depuis Telegram** (donc depuis votre téléphone),
sans ouvrir le dashboard web :
1. Envoyez `/monid` au bot pour obtenir votre identifiant Telegram ;
2. Ajoutez-le dans `.env` : `ADMIN_TELEGRAM_IDS=123456789` ;
3. Redémarrez le bot. Vous avez alors accès à :

| Commande | Effet |
|---|---|
| `/admin` | Statistiques générales (membres, matchs, taux d'acceptation…) |
| `/membres [recherche]` | Liste ou recherche de membres |
| `/fiche <id>` | Fiche complète d'un membre |
| `/matchs` | Derniers matchs avec scores et statuts |
| `/conv <id>` | Derniers échanges bot ↔ membre (modération) |
| `/publier question\|quiz\|regles\|stats` | Publier immédiatement dans le groupe |

Les commandes sont invisibles et inertes pour les non-administrateurs.

### 🖥️ Tableau de bord administrateur local (`app/webadmin.py`)
Backend **FastAPI** qui tourne en local et sert à la fois une **API REST**
(`/api/…`, documentation interactive sur `/api/docs`) et une **interface web**
(`http://localhost:8000`) :
- **Statistiques** : total, répartition H/F, actifs, incomplets, nouveaux
  inscrits, matchs générés, taux d'acceptation, graphiques.
- **Utilisateurs** : recherche avancée (âge, sexe, ville, département, pays,
  situation, profession, complétude, statut), fiche détaillée complète.
- **Matchs** : proposés / acceptés / refusés, scores et décomposition.
- **Conversations** : historique bot ↔ membre (accès encadré, mention RGPD).
- Protégé par mot de passe (`ADMIN_PASSWORD`, authentification HTTP Basic —
  l'identifiant est libre).

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# puis éditez .env et renseignez les valeurs
```

Variables indispensables dans `.env` :

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Jeton obtenu auprès de [@BotFather](https://t.me/BotFather) |
| `ANTHROPIC_API_KEY` | Clé API [Claude](https://platform.claude.com) |
| `ADMIN_PASSWORD` | Mot de passe du dashboard |
| `COMMUNITY_CHAT_ID` | *(optionnel)* ID du groupe pour l'animation |

## Lancement

```bash
# 1. Le bot Telegram (conversations + matching + animation)
python3 -m app.bot

# 2. Le tableau de bord admin local (dans un autre terminal)
python3 -m app.webadmin
# puis ouvrez http://localhost:8000  (API REST : http://localhost:8000/api/docs)
```

Le bot et le dashboard partagent la même base SQLite (`data/app.db` par défaut,
configurable via `DATABASE_URL` — PostgreSQL supporté).

## Données de démonstration

Pour tester le matching et le dashboard sans attendre de vrais utilisateurs :

```bash
python3 -m scripts.seed_demo
```

## Architecture

```
app/
├── config.py          # configuration (.env)
├── db.py              # modèles SQLAlchemy (users, profils, messages, matchs…)
├── profile_schema.py  # schéma du profil, pondérations de l'indice 0-100
├── ai.py              # conversation + extraction structurée (API Claude)
├── matching.py        # moteur de compatibilité 3 niveaux
├── bot.py             # bot Telegram (handlers + jobs planifiés)
├── webadmin.py        # backend admin local (FastAPI : API REST + interface web)
└── static/admin.html  # interface web du tableau de bord
scripts/seed_demo.py   # données de démonstration
```

## Déploiement sur un VPS (Debian/Ubuntu)

```bash
# Sur le serveur :
apt-get update && apt-get install -y git
git clone -b claude/muslim-matchmaking-telegram-0onyu1 https://github.com/anis66ben/blank-app.git /opt/rencontre
bash /opt/rencontre/deploy/install.sh     # services systemd isolés (rencontre-*)
nano /opt/rencontre/.env                  # renseigner les secrets
systemctl restart rencontre-bot rencontre-webadmin

# HTTPS pour l'accès smartphone (certificat automatique, domaine optionnel) :
bash /opt/rencontre/deploy/setup-https.sh            # -> https://<ip-tirets>.sslip.io
bash /opt/rencontre/deploy/setup-https.sh mondomaine.fr

# Mises à jour ultérieures :
bash /opt/rencontre/deploy/update.sh
```

Tout est isolé dans `/opt/rencontre` (utilisateur système dédié, venv propre,
port choisi automatiquement parmi les ports libres) : aucune interférence avec
d'autres applications présentes sur le serveur.

## Respect des données personnelles

- L'accès aux conversations depuis le dashboard est réservé à la modération
  (signalements, sécurité) — informez vos membres dans vos CGU et conformez-vous
  au RGPD (droit d'accès, de rectification et d'effacement).
- Les publications communautaires (profil de la semaine, statistiques) sont
  anonymisées.
