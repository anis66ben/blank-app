# 🌙 Plateforme de mise en relation entre musulmans — Bot Telegram + Dashboard admin

Plateforme de rencontre sérieuse (en vue du mariage) utilisant **Telegram** comme
interface principale. Le bot construit un **profil riche** de chaque membre à
travers des **conversations naturelles** (propulsées par l'API Claude), propose
des profils compatibles grâce à un **moteur de matching**, anime la communauté,
et fournit à l'administrateur un **tableau de bord web local** (FastAPI, aucun
service externe requis).

## Fonctionnalités

### 🧬 Persona & journal d'étude
Le comportement conversationnel du bot est défini par un prompt « expert en
découverte de personnalité » isolé dans **`app/persona.py`** (facile à étudier
et ajuster) : conversation naturelle plutôt que questionnaire, histoires plutôt
qu'opinions, exploration progressive (identité, valeurs, vision du monde,
relations, mode de vie, aspirations), mémoire structurée par hypothèses.

Chaque tour est enregistré dans **`data/conversation_log.jsonl`** (`app/convlog.py`)
pour étudier le modèle : message reçu, sortie brute, réponse, infos extraites,
préférences détectées, durée, repli éventuel. Consultable depuis le téléphone
via la commande **`/journal [n]`**, ou en ouvrant le fichier
(`cat data/conversation_log.jsonl`). Désactivable avec `CONVERSATION_LOG=false`.

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
- **RGPD** : consentement demandé au `/start` (`CONSENT_REQUIRED`), `/mesdonnees`
  (droit d'accès), `/supprimer` (droit à l'effacement), `/conditions` (rappel).
- **Maîtrise des coûts** : plafond de messages IA par membre et par jour
  (`MAX_MESSAGES_PER_DAY`, défaut 40) — anti-flood et budget maîtrisé.

### 🧠 Moteur IA : Claude, Qwen3 local, ou mode guidé
Le bot fonctionne avec quatre moteurs interchangeables (`LLM_PROVIDER` dans `.env`) :

| `LLM_PROVIDER` | Moteur | Coût / confidentialité |
|---|---|---|
| `mlx` | **Qwen3 4B (4-bit) en local via MLX** — Apple Silicon | Gratuit, 100 % privé, optimisé M1/M2/M3 |
| `ollama` | Qwen3 en local via [Ollama](https://ollama.com) | Gratuit, 100 % privé |
| `claude` | API Anthropic (Claude) | Payant, qualité maximale |
| `none` | Questionnaire guidé (`app/scripted.py`) | Gratuit, sans IA (questions prédéfinies) |
| *(vide)* | Auto : Claude si clé, sinon Ollama si joignable, sinon guidé | — |

La couche `app/llm.py` unifie les moteurs : conversation structurée, texte
libre, embeddings. Le profil, l'indice de connaissance, le matching et le
dashboard fonctionnent à l'identique quel que soit le moteur.

**Option recommandée sur Mac Apple Silicon — MLX (le plus rapide, sans Ollama) :**
```bash
pip install -r requirements-mlx.txt         # installe mlx-lm
pip install "transformers>=4.51,<5.0"       # version compatible (voir note ci-dessous)
# Dans .env : LLM_PROVIDER=mlx  (déjà par défaut dans .env.example)
```
> ℹ️ `mlx-lm 0.31.3` déclare `transformers>=5.0` mais plante à l'import avec la
> 5.0 (bug amont). On force donc une `transformers` 4.5x qui fonctionne et
> supporte Qwen3. L'avertissement pip « dependency resolver… » est sans effet.
Le modèle `mlx-community/Qwen3-4B-4bit` (~2,3 Go) se télécharge automatiquement
au premier lancement (cache Hugging Face `~/.cache/huggingface/`), puis tourne
directement dans le processus Python — aucun service externe, aucune donnée qui
sort de la machine. Le raisonnement Qwen3 est désactivé (`enable_thinking=False`)
pour des réponses rapides. Le modèle est préchargé au démarrage du bot.

**Alternative — Ollama :**
```bash
# Installer Ollama : https://ollama.com/download
ollama pull qwen3:4b            # conversation
ollama pull nomic-embed-text    # embeddings (RAG)
# Dans .env : LLM_PROVIDER=ollama
```
Avec MLX comme avec Ollama, le bot doit tourner sur la machine qui héberge le
modèle.

### 🗂️ RAG — mémoire vectorielle (fenêtre de contexte déportée)
Avec **Ollama**, le RAG (`app/rag.py`) est actif automatiquement : au lieu
d'entasser tout l'historique dans le prompt, chaque souvenir (fait, réaction,
préférence) est stocké sous forme de vecteur dans la table `memory_chunks` ; à
chaque message, seuls les `RAG_TOP_K` souvenirs les plus pertinents sont
réinjectés. Le contexte « vit » dans la base, pas dans le prompt.

Avec **MLX**, le RAG est actif en deux modes (choisis automatiquement) :
- **Sémantique** si vous installez le petit modèle d'embeddings
  (`pip install -r requirements-rag.txt`) : similarité vectorielle, comprend les
  reformulations. ⚠️ embarque PyTorch (~1-2 Go) — sur un Mac 8 Go où tourne déjà
  le LLM, ça peut être juste.
- **Lexical** sinon (par défaut, zéro dépendance) : recouvrement de mots-clés
  avec racinisation française légère (famille/familial se rejoignent). Fonctionne
  tout de suite, léger, et déporte réellement la mémoire hors du prompt.

Dans les deux cas, la mémoire du membre (faits, réactions, préférences, échanges
marquants) vit dans la table `memory_chunks`, **pas dans le prompt** : à chaque
message, seuls les souvenirs pertinents sont récupérés et réinjectés. Le bot
garde donc le fil de toute la relation sans alourdir la fenêtre de contexte.
Réglages : `RAG_ENABLED`, `RAG_TOP_K`, `EMBED_MODEL` dans `.env`.

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

## Modération

- Bouton **🚩 Signaler** sur chaque suggestion de profil, et commande
  **`/signaler <description>`** pour tout comportement déplacé.
- Un signalement **exclut définitivement la paire** du moteur de matching.
- Les administrateurs sont notifiés en temps réel et disposent de
  **`/signalements`** (Telegram) pour la revue.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```
Le socle (`tests/`) couvre la complétude des profils, le moteur de matching
(filtres, score, machine à états, exclusion par signalement), le RGPD (plafond,
export, suppression) et le mode guidé + extraction JSON. Base SQLite jetable,
aucun appel réseau.

## Respect des données personnelles

- L'accès aux conversations depuis le dashboard est réservé à la modération
  (signalements, sécurité) — informez vos membres dans vos CGU et conformez-vous
  au RGPD (droit d'accès, de rectification et d'effacement).
- Les publications communautaires (profil de la semaine, statistiques) sont
  anonymisées.
