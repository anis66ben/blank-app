import type {
  CleaningTask,
  Incident,
  Property,
  Provider,
  Reservation,
} from "./types";
import { isSameDay } from "./utils";

export function reservationsEndingToday(reservations: Reservation[]): Reservation[] {
  const today = new Date();
  return reservations.filter((r) => isSameDay(new Date(r.endDate), today));
}

export function reservationsStartingToday(reservations: Reservation[]): Reservation[] {
  const today = new Date();
  return reservations.filter((r) => isSameDay(new Date(r.startDate), today));
}

export function tasksToday(tasks: CleaningTask[]): CleaningTask[] {
  const today = new Date();
  return tasks.filter((t) => isSameDay(new Date(t.date), today));
}

export function openIncidents(incidents: Incident[]): Incident[] {
  return incidents.filter((i) => i.status !== "resolved");
}

// Retards : missions du jour non terminées dont l'heure de fin est dépassée.
export function lateTasks(tasks: CleaningTask[]): CleaningTask[] {
  const now = new Date();
  return tasksToday(tasks).filter(
    (t) =>
      t.status !== "done" &&
      t.status !== "incident" &&
      new Date(t.endTime) < now,
  );
}

export function unassignedTasks(tasks: CleaningTask[]): CleaningTask[] {
  return tasks.filter((t) => t.status === "todo" || !t.providerId);
}

export function availableProviders(providers: Provider[]): Provider[] {
  return [...providers]
    .filter((p) => p.availabilityScore >= 0.5)
    .sort((a, b) => b.availabilityScore - a.availabilityScore);
}

// Calcul de la fenêtre disponible : départ client → temps ménage → arrivée suivante.
export function availableWindow(
  property: Property,
  reservations: Reservation[],
): { departure: Reservation | null; nextArrival: Reservation | null; gapHours: number | null } {
  const today = new Date();
  const propRes = reservations
    .filter((r) => r.propertyId === property.id)
    .sort((a, b) => +new Date(a.startDate) - +new Date(b.startDate));

  const departure =
    propRes.find((r) => isSameDay(new Date(r.endDate), today)) ?? null;
  if (!departure) return { departure: null, nextArrival: null, gapHours: null };

  const nextArrival =
    propRes.find((r) => new Date(r.startDate) >= new Date(departure.endDate)) ??
    null;

  const gapHours = nextArrival
    ? (+new Date(nextArrival.startDate) - +new Date(departure.endDate)) /
      36e5
    : null;

  return { departure, nextArrival, gapHours };
}
