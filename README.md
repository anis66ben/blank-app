# 🏔️ Concierge Flow

**SaaS de gestion de conciergerie et de location saisonnière.**
Centralise toute l'exploitation quotidienne (réservations, ménages, prestataires,
incidents, WhatsApp) dans une seule interface premium — sans jamais ouvrir Excel
ou WhatsApp séparément. Conçu pour superviser de 50 à 500 logements.

> Remplace l'empilement Airbnb + Booking + WhatsApp + Excel + téléphone par une
> unique **tour de contrôle**.

## ✨ Fonctionnalités

- **Tour de contrôle** — cartes KPI (logements, départs/arrivées du jour, missions
  en cours, incidents, retards) + flux temps réel + panneau d'action.
- **Planning Gantt** — vue logements (1 ligne / logement, barres colorées par
  statut) et vue prestataires avec **réassignation par glisser-déposer** et
  équilibrage des charges. Zoom jour / semaine / mois.
- **Missions ménage** — création auto au départ d'un voyageur, filtres
  (aujourd'hui / demain / en retard / urgents), changement de statut, et
  **attribution automatique** scorée (disponibilité 40 % · zone 30 % · note 20 %
  · charge 10 %).
- **Logements** — fiche complète avec onglets Calendrier, Missions, WhatsApp,
  Photos (avant/après) et Incidents. Calcul de la fenêtre disponible
  (départ → ménage → arrivée suivante).
- **Prestataires** — note, zone, disponibilité, charge journalière.
- **Incidents** — tickets typés (ampoule, fuite, télévision, vaisselle, dégâts
  voyageur) et niveaux (faible / moyen / urgent).
- **WhatsApp** — message automatique à la création d'une mission, réponse `OUI`
  pour accepter, réception photos/commentaires (logique dans `lib/whatsapp.ts`).
- **Assistant IA** — répond aux questions opérationnelles (retards, prestataire le
  plus fiable, maintenance, missions de demain, rédaction WhatsApp).
- **Design premium** — mode clair / sombre, cartes arrondies, animations, responsive.

## 🧱 Stack

- **Frontend** : Next.js 15 (App Router) · TypeScript · TailwindCSS · UI façon Shadcn
- **État** : Zustand
- **Backend cible** : Supabase (PostgreSQL · Auth · Storage · Realtime)
- **Cartographie** : Mapbox · **Messagerie** : WhatsApp Business API · **IA** : API Claude

> ℹ️ La démo fonctionne **sans backend** : les données sont en mémoire
> (`lib/mock-data.ts`) afin que l'application tourne immédiatement. Le schéma
> Supabase est fourni dans `supabase/schema.sql` et les points d'intégration
> (Supabase, WhatsApp, IA) sont isolés dans `lib/` pour un branchement progressif.

## 🚀 Démarrage

```bash
npm install
npm run dev          # http://localhost:3000
```

Build de production :

```bash
npm run build && npm start
```

### Brancher Supabase / WhatsApp / IA

1. Copier `.env.example` vers `.env.local` et renseigner les clés.
2. Exécuter `supabase/schema.sql` dans l'éditeur SQL Supabase.
3. Activer le client dans `lib/supabase.ts` et remplacer les sélecteurs du store
   par des requêtes Supabase.

## 📁 Structure

```
app/
  page.tsx              → Tour de contrôle (dashboard)
  planning/             → Gantt logements + prestataires
  tasks/                → missions ménage + attribution
  properties/[id]/      → fiche logement (onglets)
  providers/            → prestataires
  incidents/            → tickets incidents
  assistant/            → assistant IA
components/  ui · layout · dashboard · gantt
lib/        types · utils · selectors · assignment · whatsapp · assistant · supabase
store/      useStore.ts (Zustand)
supabase/   schema.sql
```

## 🗺️ Roadmap (ordre de build du cahier des charges)

1. **Fondation** : schéma Supabase · auth · logements · réservations
2. **Cœur produit** : missions ménage · attribution · dashboard
3. **UX forte** : Gantt · incidents · fiche logement
4. **Automation** : WhatsApp · attribution auto
5. **IA** : assistant opérationnel
