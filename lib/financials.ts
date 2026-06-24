import type { Intervention, Provider, ServiceType } from "./types";

// ─── Helpers de fenêtre temporelle ───────────────────────────────────────────

function startOf(unit: "day" | "week" | "month" | "year"): Date {
  const d = new Date();
  if (unit === "day") { d.setHours(0, 0, 0, 0); return d; }
  if (unit === "week") {
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); // lundi
    return d;
  }
  if (unit === "month") { d.setDate(1); d.setHours(0, 0, 0, 0); return d; }
  d.setMonth(0, 1); d.setHours(0, 0, 0, 0); return d;
}

function inWindow(date: string, from: Date): boolean {
  return new Date(date) >= from;
}

// ─── CA & Coût ───────────────────────────────────────────────────────────────

export function totalRevenue(
  interventions: Intervention[],
  from?: Date,
  status?: ("done" | "invoiced" | "planned")[],
): number {
  return interventions
    .filter((i) => {
      if (from && !inWindow(i.date, from)) return false;
      if (status && !status.includes(i.status as "done" | "invoiced" | "planned")) return false;
      return true;
    })
    .reduce((s, i) => s + i.amountBilled, 0);
}

export function totalLabourCost(
  interventions: Intervention[],
  providers: Provider[],
  from?: Date,
  status?: ("done" | "invoiced" | "planned")[],
): number {
  return interventions
    .filter((i) => {
      if (from && !inWindow(i.date, from)) return false;
      if (status && !status.includes(i.status as "done" | "invoiced" | "planned")) return false;
      return true;
    })
    .reduce((s, i) => {
      const pr = providers.find((p) => p.id === i.providerId);
      return s + (pr ? (i.durationMinutes / 60) * pr.hourlyRate : 0);
    }, 0);
}

// ─── KPIs principaux ─────────────────────────────────────────────────────────

export interface FinancialKPIs {
  caDay: number;
  caWeek: number;
  caMonth: number;
  caYear: number;
  caRealised: number; // done + invoiced (toutes périodes)
  caForecast: number; // planned (toutes périodes)
  labourCostTotal: number;
  grossProfit: number;
  grossMarginPct: number;
}

export function computeKPIs(
  interventions: Intervention[],
  providers: Provider[],
): FinancialKPIs {
  const realised = interventions.filter((i) =>
    ["done", "invoiced"].includes(i.status),
  );
  const planned = interventions.filter((i) => i.status === "planned");

  const caRealised = realised.reduce((s, i) => s + i.amountBilled, 0);
  const caForecast = planned.reduce((s, i) => s + i.amountBilled, 0);
  const labourCostTotal = totalLabourCost(realised, providers);
  const grossProfit = caRealised - labourCostTotal;

  return {
    caDay: totalRevenue(realised, startOf("day")),
    caWeek: totalRevenue(realised, startOf("week")),
    caMonth: totalRevenue(realised, startOf("month")),
    caYear: totalRevenue(realised, startOf("year")),
    caRealised,
    caForecast,
    labourCostTotal,
    grossProfit,
    grossMarginPct:
      caRealised > 0 ? Math.round((grossProfit / caRealised) * 100) : 0,
  };
}

// ─── Séries temporelles (30 jours) pour graphiques ───────────────────────────

export interface DaySeries {
  date: string; // "DD/MM"
  ca: number;
  cost: number;
  profit: number;
}

export function buildDailySeries(
  interventions: Intervention[],
  providers: Provider[],
  days = 30,
): DaySeries[] {
  const result: DaySeries[] = [];
  const realised = interventions.filter((i) =>
    ["done", "invoiced"].includes(i.status),
  );
  for (let d = days - 1; d >= 0; d--) {
    const ref = new Date();
    ref.setDate(ref.getDate() - d);
    ref.setHours(0, 0, 0, 0);
    const next = new Date(ref);
    next.setDate(next.getDate() + 1);

    const dayInts = realised.filter((i) => {
      const dt = new Date(i.date);
      return dt >= ref && dt < next;
    });

    const ca = dayInts.reduce((s, i) => s + i.amountBilled, 0);
    const cost = dayInts.reduce((s, i) => {
      const pr = providers.find((p) => p.id === i.providerId);
      return s + (pr ? (i.durationMinutes / 60) * pr.hourlyRate : 0);
    }, 0);
    result.push({
      date: ref.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" }),
      ca: Math.round(ca),
      cost: Math.round(cost),
      profit: Math.round(ca - cost),
    });
  }
  return result;
}

// ─── Répartition par prestation ──────────────────────────────────────────────

export interface ServiceShare {
  name: string;
  ca: number;
  hours: number;
}

export function revenueByService(
  interventions: Intervention[],
  serviceTypes: ServiceType[],
): ServiceShare[] {
  const map = new Map<string, ServiceShare>();
  interventions
    .filter((i) => ["done", "invoiced"].includes(i.status))
    .forEach((i) => {
      const svc = serviceTypes.find((s) => s.id === i.serviceTypeId);
      if (!svc) return;
      const existing = map.get(svc.id) ?? { name: svc.name, ca: 0, hours: 0 };
      map.set(svc.id, {
        ...existing,
        ca: existing.ca + i.amountBilled,
        hours: existing.hours + i.durationMinutes / 60,
      });
    });
  return [...map.values()].sort((a, b) => b.ca - a.ca);
}

// ─── Coût MO par prestataire ─────────────────────────────────────────────────

export interface ProviderCost {
  name: string;
  hours: number;
  cost: number;
  interventions: number;
}

export function costByProvider(
  interventions: Intervention[],
  providers: Provider[],
): ProviderCost[] {
  return providers.map((pr) => {
    const pInts = interventions.filter(
      (i) =>
        i.providerId === pr.id &&
        ["done", "invoiced"].includes(i.status),
    );
    const hours = pInts.reduce((s, i) => s + i.durationMinutes / 60, 0);
    return {
      name: pr.name,
      hours: Math.round(hours * 10) / 10,
      cost: Math.round(hours * pr.hourlyRate),
      interventions: pInts.length,
    };
  });
}

// ─── Bénéfice par logement ───────────────────────────────────────────────────

export interface PropertyProfit {
  propertyId: string;
  name: string;
  ca: number;
  cost: number;
  profit: number;
}

export function profitByProperty(
  interventions: Intervention[],
  providers: Provider[],
  propertyNames: Map<string, string>,
): PropertyProfit[] {
  const map = new Map<string, PropertyProfit>();
  interventions
    .filter((i) => ["done", "invoiced"].includes(i.status))
    .forEach((i) => {
      const pr = providers.find((p) => p.id === i.providerId);
      const cost = pr ? (i.durationMinutes / 60) * pr.hourlyRate : 0;
      const existing = map.get(i.propertyId) ?? {
        propertyId: i.propertyId,
        name: propertyNames.get(i.propertyId) ?? "—",
        ca: 0, cost: 0, profit: 0,
      };
      map.set(i.propertyId, {
        ...existing,
        ca: existing.ca + i.amountBilled,
        cost: existing.cost + cost,
        profit: existing.profit + i.amountBilled - cost,
      });
    });
  return [...map.values()]
    .map((p) => ({
      ...p,
      ca: Math.round(p.ca),
      cost: Math.round(p.cost),
      profit: Math.round(p.profit),
    }))
    .sort((a, b) => b.ca - a.ca);
}
