import type {
  CleaningTask,
  Incident,
  Intervention,
  Message,
  Property,
  Provider,
  Reservation,
  ServiceType,
  User,
} from "./types";

// Données de démonstration ancrées sur la date du jour (planning toujours pertinent).
function at(dayOffset: number, hour: number, minute = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + dayOffset);
  d.setHours(hour, minute, 0, 0);
  return d.toISOString();
}

function dateOnly(dayOffset: number): string {
  const d = new Date();
  d.setDate(d.getDate() + dayOffset);
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

export const users: User[] = [
  { id: "u1", name: "Camille Moreau", email: "camille@conciergeflow.app", role: "admin", phone: "+33611111111" },
  { id: "u2", name: "Hugo Bernard", email: "hugo@conciergeflow.app", role: "manager", phone: "+33622222222" },
  { id: "u3", name: "Fatima Z.", email: "fatima@presta.app", role: "provider", phone: "+33633333333" },
  { id: "u4", name: "Marc Petit", email: "marc.owner@gmail.com", role: "owner", phone: "+33644444444" },
];

const PHOTO = (seed: string) =>
  `https://images.unsplash.com/${seed}?auto=format&fit=crop&w=800&q=60`;

export const properties: Property[] = [
  { id: "p1", name: "Chalet A12", address: "12 Route des Pèlerins, Chamonix", capacity: 8, cleaningTime: 150, qualityCheckTime: 30, doorCode: "A1207", notes: "Jacuzzi à vérifier à chaque départ.", lat: 45.9237, lng: 6.8694, photo: PHOTO("photo-1502672260266-1c1ef2d93688"), ownerId: "u4" },
  { id: "p2", name: "Chalet B07", address: "7 Allée du Mont, Chamonix", capacity: 6, cleaningTime: 120, qualityCheckTime: 20, doorCode: "B0712", notes: "Chat du propriétaire le mardi.", lat: 45.9275, lng: 6.8721, photo: PHOTO("photo-1480074568708-e7b720bb3f09"), ownerId: "u4" },
  { id: "p3", name: "Chalet C02", address: "2 Chemin des Bois, Megève", capacity: 10, cleaningTime: 180, qualityCheckTime: 40, doorCode: "C0299", notes: "Cheminée — prévoir bûches.", lat: 45.8566, lng: 6.6177, photo: PHOTO("photo-1449844908441-8829872d2607"), ownerId: "u4" },
  { id: "p4", name: "Appart Annecy Lac", address: "5 Quai Jules Philippe, Annecy", capacity: 4, cleaningTime: 90, qualityCheckTime: 15, doorCode: "L4501", notes: "Parking au sous-sol, place 14.", lat: 45.8992, lng: 6.1294, photo: PHOTO("photo-1502005229762-cf1b2da7c5d6"), ownerId: "u4" },
  { id: "p5", name: "Studio Megève Centre", address: "18 Rue Charles Feige, Megève", capacity: 2, cleaningTime: 60, qualityCheckTime: 10, doorCode: "MG18", notes: "", lat: 45.857, lng: 6.6173, photo: PHOTO("photo-1522708323590-d24dbb6b0267"), ownerId: "u4" },
  { id: "p6", name: "Chalet Panorama", address: "30 Route Blanche, Chamonix", capacity: 12, cleaningTime: 200, qualityCheckTime: 45, doorCode: "PAN30", notes: "Spa extérieur, sauna.", lat: 45.93, lng: 6.86, photo: PHOTO("photo-1518780664697-55e3ad937233"), ownerId: "u4" },
];

export const providers: Provider[] = [
  { id: "pr1", name: "Fatima Z.", phone: "+33633333333", zone: "Chamonix", rating: 4.8, availabilityScore: 0.9, currentLoad: 1, hourlyRate: 18 },
  { id: "pr2", name: "Léa Dubois", phone: "+33655555555", zone: "Chamonix", rating: 4.5, availabilityScore: 0.6, currentLoad: 3, hourlyRate: 16 },
  { id: "pr3", name: "Sofiane K.", phone: "+33666666666", zone: "Megève", rating: 4.2, availabilityScore: 0.8, currentLoad: 2, hourlyRate: 17 },
  { id: "pr4", name: "Marta Silva", phone: "+33677777777", zone: "Annecy", rating: 4.9, availabilityScore: 0.7, currentLoad: 0, hourlyRate: 19 },
  { id: "pr5", name: "Yanis B.", phone: "+33688888888", zone: "Megève", rating: 4.0, availabilityScore: 0.5, currentLoad: 4, hourlyRate: 15 },
];

export const reservations: Reservation[] = [
  { id: "r1", propertyId: "p1", platform: "airbnb", guestName: "Famille Laurent", startDate: dateOnly(-4), endDate: dateOnly(0), guestsCount: 6 },
  { id: "r2", propertyId: "p1", platform: "booking", guestName: "M. Schmidt", startDate: dateOnly(0), endDate: dateOnly(3), guestsCount: 4 },
  { id: "r3", propertyId: "p2", platform: "airbnb", guestName: "Couple Rossi", startDate: dateOnly(-2), endDate: dateOnly(0), guestsCount: 2 },
  { id: "r4", propertyId: "p2", platform: "abritel", guestName: "Famille Nguyen", startDate: dateOnly(0), endDate: dateOnly(5), guestsCount: 5 },
  { id: "r5", propertyId: "p3", platform: "booking", guestName: "Groupe Ski Lyon", startDate: dateOnly(-3), endDate: dateOnly(0), guestsCount: 9 },
  { id: "r6", propertyId: "p3", platform: "airbnb", guestName: "Famille Garcia", startDate: dateOnly(1), endDate: dateOnly(6), guestsCount: 8 },
  { id: "r7", propertyId: "p4", platform: "airbnb", guestName: "M. & Mme Petit", startDate: dateOnly(-1), endDate: dateOnly(0), guestsCount: 3 },
  { id: "r8", propertyId: "p5", platform: "booking", guestName: "Julie Martin", startDate: dateOnly(0), endDate: dateOnly(2), guestsCount: 2 },
  { id: "r9", propertyId: "p6", platform: "abritel", guestName: "Séminaire TechCorp", startDate: dateOnly(-5), endDate: dateOnly(0), guestsCount: 11 },
];

export const cleaningTasks: CleaningTask[] = [
  { id: "t1", propertyId: "p1", reservationId: "r1", providerId: "pr1", date: dateOnly(0), startTime: at(0, 11, 0), endTime: at(0, 13, 30), status: "accepted", priority: "high", estimatedTime: 150 },
  { id: "t2", propertyId: "p2", reservationId: "r3", providerId: null, date: dateOnly(0), startTime: at(0, 11, 30), endTime: at(0, 13, 30), status: "todo", priority: "high", estimatedTime: 120 },
  { id: "t3", propertyId: "p3", reservationId: "r5", providerId: "pr3", date: dateOnly(0), startTime: at(0, 12, 0), endTime: at(0, 15, 0), status: "proposed", priority: "medium", estimatedTime: 180 },
  { id: "t4", propertyId: "p4", reservationId: "r7", providerId: "pr4", date: dateOnly(0), startTime: at(0, 10, 0), endTime: at(0, 11, 30), status: "in_progress", priority: "medium", estimatedTime: 90 },
  { id: "t5", propertyId: "p6", reservationId: "r9", providerId: "pr2", date: dateOnly(0), startTime: at(0, 9, 0), endTime: at(0, 12, 20), status: "incident", priority: "high", estimatedTime: 200 },
  { id: "t6", propertyId: "p5", reservationId: null, providerId: "pr3", date: dateOnly(0), startTime: at(0, 14, 0), endTime: at(0, 15, 0), status: "done", priority: "low", estimatedTime: 60 },
  { id: "t7", propertyId: "p3", reservationId: "r6", providerId: null, date: dateOnly(1), startTime: at(1, 9, 30), endTime: at(1, 12, 30), status: "todo", priority: "high", estimatedTime: 180 },
  { id: "t8", propertyId: "p1", reservationId: "r2", providerId: "pr1", date: dateOnly(3), startTime: at(3, 11, 0), endTime: at(3, 13, 30), status: "accepted", priority: "medium", estimatedTime: 150 },
];

export const incidents: Incident[] = [
  { id: "i1", propertyId: "p6", taskId: "t5", type: "fuite", severity: "high", description: "Fuite sous l'évier de la cuisine, eau au sol.", status: "open", createdAt: at(0, 9, 45) },
  { id: "i2", propertyId: "p3", taskId: null, type: "television", severity: "medium", description: "TV du salon ne s'allume plus.", status: "in_progress", createdAt: at(-1, 16, 0) },
  { id: "i3", propertyId: "p1", taskId: null, type: "ampoule", severity: "low", description: "Ampoule grillée dans la chambre 2.", status: "resolved", createdAt: at(-2, 10, 0) },
  { id: "i4", propertyId: "p2", taskId: null, type: "degats_voyageur", severity: "high", description: "Tâche sur le canapé signalée par le voyageur précédent.", status: "open", createdAt: at(0, 8, 30) },
];

export const messages: Message[] = [
  { id: "m1", providerId: "pr1", propertyId: "p1", taskId: "t1", direction: "out", content: "Bonjour.\nMission disponible :\nChalet A12\nAujourd'hui\n11h00 à 13h30\nRépondez OUI pour accepter.", mediaUrl: null, createdAt: at(-1, 18, 0) },
  { id: "m2", providerId: "pr1", propertyId: "p1", taskId: "t1", direction: "in", content: "OUI", mediaUrl: null, createdAt: at(-1, 18, 5) },
  { id: "m3", providerId: "pr1", propertyId: "p1", taskId: "t1", direction: "in", content: "Ménage terminé ✅ photos jointes", mediaUrl: PHOTO("photo-1556228453-efd6c1ff04f6"), createdAt: at(0, 13, 25) },
  { id: "m4", providerId: "pr2", propertyId: "p6", taskId: "t5", direction: "in", content: "Problème : fuite sous l'évier, je signale un incident.", mediaUrl: PHOTO("photo-1607472586893-edb57bdc0e39"), createdAt: at(0, 9, 45) },
];

// ─── Catalogue de prestations ─────────────────────────────────────────────────

export const serviceTypes: ServiceType[] = [
  { id: "s1", name: "Ménage standard", price: 120, unit: "forfait", category: "menage" },
  { id: "s2", name: "Ménage grande capacité", price: 180, unit: "forfait", category: "menage" },
  { id: "s3", name: "Blanchisserie", price: 35, unit: "intervention", category: "blanchisserie" },
  { id: "s4", name: "Location de linge (kit)", price: 25, unit: "nuitee", category: "linge" },
  { id: "s5", name: "Tonte de gazon", price: 60, unit: "intervention", category: "jardin" },
  { id: "s6", name: "Entretien extérieur", price: 45, unit: "heure", category: "jardin" },
  { id: "s7", name: "Maintenance légère", price: 50, unit: "heure", category: "maintenance" },
  { id: "s8", name: "Contrôle qualité", price: 40, unit: "forfait", category: "menage" },
  { id: "s9", name: "Accueil voyageurs", price: 30, unit: "intervention", category: "autre" },
];

// ─── 30 jours d'historique d'interventions (déterministe) ────────────────────

const PROP_IDS = ["p1", "p2", "p3", "p4", "p5", "p6"];
const PROV_IDS = ["pr1", "pr2", "pr3", "pr4", "pr5"];
// Pattern par jour : [propertyIdx, serviceIdx, providerIdx, durationMin, amountBilled, status]
// 5 interventions par jour, statut "done" ou "invoiced" pour l'historique.
const DAILY_PATTERN: [number, number, number, number, number][] = [
  [0, 0, 0, 150, 120],
  [1, 0, 1, 120, 120],
  [2, 1, 2, 180, 180],
  [3, 2, 3, 45, 35],
  [4, 3, 4, 30, 25],
];

function buildInterventions(): Intervention[] {
  const result: Intervention[] = [];
  for (let day = -29; day <= -1; day++) {
    const d = new Date();
    d.setDate(d.getDate() + day);
    d.setHours(0, 0, 0, 0);
    const dateStr = d.toISOString();
    DAILY_PATTERN.forEach(([pi, si, pri, dur, amount], idx) => {
      // Vary amounts slightly using day offset to make charts interesting
      const factor = 1 + ((((day + 29) * (idx + 1)) % 5) - 2) * 0.06;
      const billedAmount = Math.round(amount * factor);
      result.push({
        id: `iv${Math.abs(day)}_${idx}`,
        propertyId: PROP_IDS[pi % PROP_IDS.length],
        serviceTypeId: serviceTypes[si % serviceTypes.length].id,
        taskId: null,
        providerId: PROV_IDS[pri % PROV_IDS.length],
        date: dateStr,
        durationMinutes: dur,
        amountBilled: billedAmount,
        status: day < -3 ? "invoiced" : "done",
        notes: "",
      });
    });
  }
  // Interventions du jour (planifiées et réalisées)
  result.push(
    { id: "iv_today_0", propertyId: "p1", serviceTypeId: "s1", taskId: "t1", providerId: "pr1", date: dateOnly(0), durationMinutes: 150, amountBilled: 120, status: "done", notes: "" },
    { id: "iv_today_1", propertyId: "p2", serviceTypeId: "s3", taskId: null, providerId: "pr2", date: dateOnly(0), durationMinutes: 45, amountBilled: 35, status: "planned", notes: "" },
    { id: "iv_today_2", propertyId: "p3", serviceTypeId: "s2", taskId: "t3", providerId: "pr3", date: dateOnly(0), durationMinutes: 180, amountBilled: 180, status: "planned", notes: "" },
    { id: "iv_today_3", propertyId: "p4", serviceTypeId: "s1", taskId: "t4", providerId: "pr4", date: dateOnly(0), durationMinutes: 90, amountBilled: 120, status: "done", notes: "" },
    { id: "iv_today_4", propertyId: "p6", serviceTypeId: "s4", taskId: null, providerId: "pr1", date: dateOnly(0), durationMinutes: 30, amountBilled: 50, status: "planned", notes: "" },
  );
  return result;
}

export const interventions: Intervention[] = buildInterventions();
