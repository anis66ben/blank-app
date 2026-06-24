import { scoreProviders } from "./assignment";
import { buildMissionMessage } from "./whatsapp";
import {
  lateTasks,
  reservationsEndingToday,
  tasksToday,
} from "./selectors";
import type {
  CleaningTask,
  Incident,
  Property,
  Provider,
  Reservation,
} from "./types";

interface Ctx {
  properties: Property[];
  providers: Provider[];
  tasks: CleaningTask[];
  incidents: Incident[];
  reservations: Reservation[];
}

// Assistant opérationnel — moteur de réponses local (sans clé API).
// Pour brancher l'API Claude : appeler une route /api/assistant qui transmet
// ce contexte au modèle (claude-fable-5) et renvoie la réponse en streaming.
export function answerQuestion(question: string, ctx: Ctx): string {
  const q = question.toLowerCase();
  const propName = (id: string) =>
    ctx.properties.find((p) => p.id === id)?.name ?? "—";

  if (q.includes("retard")) {
    const late = lateTasks(ctx.tasks);
    if (late.length === 0) return "Aucun logement en retard actuellement. 🎉";
    return (
      "Logements en retard :\n" +
      late.map((t) => `• ${propName(t.propertyId)}`).join("\n")
    );
  }

  if (q.includes("fiable") || q.includes("meilleur prestataire")) {
    const best = [...ctx.providers].sort((a, b) => b.rating - a.rating)[0];
    return best
      ? `Le prestataire le plus fiable est ${best.name} (note ★ ${best.rating}, zone ${best.zone}).`
      : "Aucun prestataire enregistré.";
  }

  if (q.includes("maintenance") || q.includes("entretien")) {
    const needing = ctx.incidents.filter((i) => i.status !== "resolved");
    if (needing.length === 0) return "Aucun logement ne nécessite de maintenance.";
    return (
      "Logements nécessitant une maintenance :\n" +
      needing
        .map((i) => `• ${propName(i.propertyId)} — ${i.type} (${i.severity})`)
        .join("\n")
    );
  }

  if (q.includes("demain")) {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const upcoming = ctx.tasks.filter(
      (t) =>
        new Date(t.date).toDateString() === tomorrow.toDateString(),
    );
    if (upcoming.length === 0) return "Aucune mission prévue demain.";
    return (
      "Missions de demain :\n" +
      upcoming
        .map((t) => {
          const prop = ctx.properties.find((p) => p.id === t.propertyId);
          const suggestion =
            !t.providerId && prop
              ? ` → suggéré : ${scoreProviders(prop, ctx.providers)[0]?.provider.name}`
              : "";
          return `• ${propName(t.propertyId)}${suggestion}`;
        })
        .join("\n")
    );
  }

  if (q.includes("whatsapp") || q.includes("message") || q.includes("rédige")) {
    const todays = tasksToday(ctx.tasks).filter((t) => t.status === "todo");
    const target = todays[0];
    const prop = target
      ? ctx.properties.find((p) => p.id === target.propertyId)
      : undefined;
    if (target && prop) {
      return "Brouillon WhatsApp :\n\n" + buildMissionMessage(prop, target);
    }
    return "Aucune mission à attribuer pour rédiger un message.";
  }

  // Réponse par défaut : synthèse du jour.
  const dep = reservationsEndingToday(ctx.reservations).length;
  const open = ctx.incidents.filter((i) => i.status !== "resolved").length;
  return `Synthèse du jour : ${tasksToday(ctx.tasks).length} mission(s), ${dep} départ(s), ${open} incident(s) ouvert(s). Posez-moi une question : retards, prestataire fiable, maintenance, missions de demain, ou rédaction WhatsApp.`;
}

export const SUGGESTED_QUESTIONS = [
  "Quels logements sont en retard ?",
  "Qui est le prestataire le plus fiable ?",
  "Quels logements nécessitent une maintenance ?",
  "Prépare les missions de demain.",
  "Rédige les messages WhatsApp.",
];
