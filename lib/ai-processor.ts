import type {
  AIAction,
  CleaningTask,
  Incident,
  Intervention,
  ProcessedMessage,
  Property,
  Provider,
  ServiceType,
} from "./types";

// ─── Contexte passé au parseur ────────────────────────────────────────────────

export interface ParseContext {
  properties: Property[];
  providers: Provider[];
  serviceTypes: ServiceType[];
  tasks: CleaningTask[];
  interventions: Intervention[];
}

// ─── Normalisation ────────────────────────────────────────────────────────────

function normalize(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/['']/g, "'");
}

// ─── Détection de propriété (fuzzy match sur le nom) ─────────────────────────

function detectProperty(
  text: string,
  properties: Property[],
): Property | null {
  const n = normalize(text);
  // Correspondance exacte d'abord
  for (const p of properties) {
    if (n.includes(normalize(p.name))) return p;
  }
  // Mots clés partiels (ex : "chalet a12", "bellevue", "annecy")
  for (const p of properties) {
    const words = normalize(p.name).split(/\s+/);
    if (words.some((w) => w.length > 3 && n.includes(w))) return p;
  }
  return null;
}

// ─── Détection du prestataire ─────────────────────────────────────────────────

function detectProvider(
  text: string,
  providers: Provider[],
): Provider | null {
  const n = normalize(text);
  for (const p of providers) {
    const parts = normalize(p.name).split(/\s+/);
    if (parts.some((w) => w.length > 2 && n.includes(w))) return p;
  }
  return null;
}

// ─── Extraction d'heure ("à 13h45", "à 13:45", "terminé 14h") ────────────────

function extractEndTime(text: string): string | null {
  const m =
    text.match(/\bà\s*(\d{1,2})[h:](\d{2})/i) ??
    text.match(/termin[eé](?:s?)?\s+(?:à\s*)?(\d{1,2})[h:](\d{2})/i) ??
    text.match(/\bfini\s+à\s*(\d{1,2})[h:](\d{2})/i);
  if (!m) {
    const hourOnly = text.match(/\bà\s*(\d{1,2})h\b/i);
    if (hourOnly) {
      const d = new Date();
      d.setHours(parseInt(hourOnly[1]), 0, 0, 0);
      return d.toISOString();
    }
    return null;
  }
  const d = new Date();
  d.setHours(parseInt(m[1]), parseInt(m[2] ?? "0"), 0, 0);
  return d.toISOString();
}

// ─── Extraction de durée ("3 heures", "2h30", "1h", "45 minutes") ─────────────

function extractDuration(text: string): number | null {
  const n = normalize(text);
  const hm = n.match(/(\d+)h(\d+)/);
  if (hm) return parseInt(hm[1]) * 60 + parseInt(hm[2]);
  const h = n.match(/(\d+(?:[.,]\d+)?)\s*heure/);
  if (h) return Math.round(parseFloat(h[1].replace(",", ".")) * 60);
  const hShort = n.match(/(\d+)h\b/);
  if (hShort) return parseInt(hShort[1]) * 60;
  const min = n.match(/(\d+)\s*min/);
  if (min) return parseInt(min[1]);
  return null;
}

// ─── Détection de completion ──────────────────────────────────────────────────

function isCompleted(text: string): boolean {
  return /termin[eé]|j'?ai fini|c'est fait|fini|effectu[eé]|fait le|fait la/i.test(text);
}

// ─── Détection de prestations ─────────────────────────────────────────────────

const SERVICE_KEYWORDS: Record<string, string[]> = {
  menage: ["menage", "nettoyage", "propre", "nettoye"],
  blanchisserie: ["blanchisserie", "lavage", "machine", "lessive"],
  linge: ["linge", "kit", "serviette", "draps"],
  jardin: ["gazon", "tonte", "jardin", "exterieur", "haie"],
  maintenance: ["reparation", "maintenance", "plomberie", "ampoule", "electrique"],
};

function detectServices(
  text: string,
  serviceTypes: ServiceType[],
): ServiceType[] {
  const n = normalize(text);
  const matched: ServiceType[] = [];
  for (const [cat, kws] of Object.entries(SERVICE_KEYWORDS)) {
    if (kws.some((kw) => n.includes(kw))) {
      const svc = serviceTypes.find((s) => s.category === cat);
      if (svc && !matched.some((m) => m.id === svc.id)) matched.push(svc);
    }
  }
  return matched;
}

// ─── Détection d'incidents ────────────────────────────────────────────────────

const INCIDENT_KEYWORDS: { pattern: RegExp; type: Incident["type"]; severity: Incident["severity"] }[] = [
  { pattern: /fuite|eau\s+au\s+sol|robinet\s+qui\s+fuit/i, type: "fuite", severity: "high" },
  { pattern: /ampoule/i, type: "ampoule", severity: "low" },
  { pattern: /t[eé]l[eé](?:vision|viseur|vision)|tv\s+(?:ne\s+)?march/i, type: "television", severity: "medium" },
  { pattern: /vaisselle\s+(?:cass|bris)/i, type: "vaisselle", severity: "low" },
  { pattern: /d[eé]g[aâ]t|d[eé]t[eé]rior[eé]|cass[eé]|bris[eé]/i, type: "degats_voyageur", severity: "medium" },
];

function detectIncident(
  text: string,
): { type: Incident["type"]; severity: Incident["severity"] } | null {
  if (!/probl[eè]me|panne|cass[eé]|bris[eé]|incident|fuite|d[eé]g[aâ]t/i.test(text)) return null;
  for (const rule of INCIDENT_KEYWORDS) {
    if (rule.pattern.test(text)) return { type: rule.type, severity: rule.severity };
  }
  return { type: "degats_voyageur", severity: "medium" };
}

// ─── Parseur principal ────────────────────────────────────────────────────────

export function processMessage(
  text: string,
  ctx: ParseContext,
): ProcessedMessage {
  const property = detectProperty(text, ctx.properties);
  const provider = detectProvider(text, ctx.providers);
  const endTime = extractEndTime(text);
  const durationMinutes = extractDuration(text);
  const services = detectServices(text, ctx.serviceTypes);
  const incident = detectIncident(text);
  const completed = isCompleted(text);

  const actions: AIAction[] = [];

  // Action 1 : mettre à jour le statut de la mission
  if (completed && property) {
    const task = ctx.tasks.find(
      (t) =>
        t.propertyId === property.id &&
        t.status !== "done" &&
        t.status !== "incident",
    );
    if (task) {
      actions.push({
        type: "update_task",
        description: `Marquer la mission de ${property.name} comme terminée${endTime ? ` (fin : ${new Date(endTime).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })})` : ""}`,
        payload: {
          taskId: task.id,
          status: "done",
          endTime: endTime ?? new Date().toISOString(),
        },
      });
    }
  }

  // Action 2 : enregistrer les heures travaillées
  if (durationMinutes && property && (provider ?? ctx.providers[0])) {
    const pr = provider ?? ctx.providers[0];
    actions.push({
      type: "log_hours",
      description: `Enregistrer ${durationMinutes} min (${(durationMinutes / 60).toFixed(1)}h) pour ${pr.name} — ${property.name}`,
      payload: {
        propertyId: property.id,
        providerId: pr.id,
        durationMinutes,
      },
    });
  }

  // Action 3 : créer intervention(s) pour les prestations détectées
  services.forEach((svc) => {
    if (!property) return;
    const pr = provider ?? ctx.providers[0];
    actions.push({
      type: "create_intervention",
      description: `Créer intervention « ${svc.name} » — ${property.name} (${svc.price} €)`,
      payload: {
        propertyId: property.id,
        serviceTypeId: svc.id,
        providerId: pr.id,
        durationMinutes: durationMinutes ?? svc.price, // fallback
        amountBilled: svc.price,
        date: new Date().toISOString(),
        status: "done",
      },
    });
  });

  // Action 4 : créer un incident
  if (incident && property) {
    actions.push({
      type: "create_incident",
      description: `Incident signalé : ${incident.type} (${incident.severity}) — ${property.name}`,
      payload: {
        propertyId: property.id,
        type: incident.type,
        severity: incident.severity,
        description: text.slice(0, 200),
      },
    });
  }

  // Calcul de confiance
  const confidence =
    actions.length >= 2 && property
      ? "high"
      : actions.length === 1 || property
        ? "medium"
        : "low";

  return {
    original: text,
    detectedProperty: property?.name ?? null,
    detectedProvider: provider?.name ?? null,
    actions,
    confidence,
    raw: {
      isCompleted: completed,
      endTime,
      durationMinutes,
      detectedServices: services.map((s) => s.name),
      detectedIncident: incident?.type ?? null,
    },
  };
}

// Messages d'exemple pour l'UI démo
export const EXAMPLE_MESSAGES = [
  "J'ai terminé le Chalet A12 à 13h45",
  "J'ai passé 3 heures au Chalet B07 et j'ai déposé deux kits de linge",
  "Ménage fini à l'Appart Annecy Lac, 2h30 de travail",
  "Problème au Chalet Panorama : fuite sous l'évier de la cuisine",
  "Fatima a terminé le Studio Megève à 11h00, blanchisserie et linge faits",
  "Chalet C02 — tonte du gazon effectuée, 1h45",
];
