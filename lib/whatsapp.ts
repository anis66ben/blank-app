import type { CleaningTask, Property, Provider } from "./types";
import { formatTime } from "./utils";

// Intégration WhatsApp Business — placeholder MVP.
// En production : appel à l'API WhatsApp Business (Meta Cloud API) via une route /api/whatsapp.
// Ici on génère le contenu du message et on le journalise.

export function buildMissionMessage(
  property: Property,
  task: CleaningTask,
): string {
  const date = new Date(task.date).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
  });
  return [
    "Bonjour.",
    "Mission disponible :",
    property.name,
    date,
    `${formatTime(task.startTime)} à ${formatTime(task.endTime)}`,
    "Répondez OUI pour accepter.",
  ].join("\n");
}

export async function sendWhatsApp(
  to: Provider,
  body: string,
): Promise<{ ok: boolean; to: string }> {
  // TODO production: POST https://graph.facebook.com/v21.0/<PHONE_ID>/messages
  // Headers: Authorization Bearer <WHATSAPP_TOKEN>
  if (process.env.NODE_ENV !== "production") {
    // eslint-disable-next-line no-console
    console.info(`[WhatsApp → ${to.phone}]\n${body}`);
  }
  return { ok: true, to: to.phone };
}

// Interprétation d'une réponse entrante (OUI / NON)
export function parseProviderReply(content: string): "accept" | "decline" | null {
  const t = content.trim().toLowerCase();
  if (["oui", "ok", "yes", "👍"].includes(t)) return "accept";
  if (["non", "no", "refuse"].includes(t)) return "decline";
  return null;
}
