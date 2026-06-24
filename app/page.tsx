"use client";

import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  Building2,
  Clock,
  ListChecks,
  PlugZap,
} from "lucide-react";
import Link from "next/link";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Topbar } from "@/components/layout/topbar";
import {
  INCIDENT_TYPE_LABEL,
  PLATFORM_BADGE,
  PLATFORM_LABEL,
  TASK_STATUS_BADGE,
  TASK_STATUS_LABEL,
} from "@/lib/constants";
import {
  availableProviders,
  lateTasks,
  openIncidents,
  reservationsEndingToday,
  reservationsStartingToday,
  tasksToday,
  unassignedTasks,
} from "@/lib/selectors";
import { formatTime } from "@/lib/utils";
import { useStore } from "@/store/useStore";

export default function DashboardPage() {
  const { properties, reservations, tasks, incidents, providers } = useStore();

  const departures = reservationsEndingToday(reservations);
  const arrivals = reservationsStartingToday(reservations);
  const todays = tasksToday(tasks);
  const inProgress = todays.filter(
    (t) => t.status === "in_progress" || t.status === "accepted",
  );
  const open = openIncidents(incidents);
  const late = lateTasks(tasks);
  const toAssign = unassignedTasks(tasks);
  const free = availableProviders(providers);

  const propName = (id: string) =>
    properties.find((p) => p.id === id)?.name ?? "—";

  // Flux temps réel : on agrège départs, arrivées, missions et incidents du jour.
  const feed = [
    ...departures.map((r) => ({
      key: `dep-${r.id}`,
      property: propName(r.propertyId),
      text: `Départ ${formatTime(r.endDate)} → ménage à prévoir`,
      tone: "blue" as const,
    })),
    ...arrivals.map((r) => ({
      key: `arr-${r.id}`,
      property: propName(r.propertyId),
      text: `Arrivée ${PLATFORM_LABEL[r.platform]} · ${r.guestsCount} voyageurs`,
      tone: "green" as const,
    })),
    ...open
      .filter((i) => i.status === "open")
      .map((i) => ({
        key: `inc-${i.id}`,
        property: propName(i.propertyId),
        text: `Incident ${i.severity === "high" ? "URGENT" : ""} · ${INCIDENT_TYPE_LABEL[i.type]}`,
        tone: "red" as const,
      })),
  ];

  return (
    <>
      <Topbar title="Tour de contrôle" />
      <div className="space-y-6 p-5">
        {/* KPI CARDS */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
          <KpiCard label="Logements" value={properties.length} icon={Building2} />
          <KpiCard
            label="Départs aujourd'hui"
            value={departures.length}
            icon={ArrowUpRight}
            accent="bg-blue-500/10 text-blue-600 dark:text-blue-400"
          />
          <KpiCard
            label="Arrivées aujourd'hui"
            value={arrivals.length}
            icon={ArrowDownLeft}
            accent="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
          />
          <KpiCard
            label="Missions en cours"
            value={inProgress.length}
            icon={ListChecks}
            accent="bg-violet-500/10 text-violet-600 dark:text-violet-400"
          />
          <KpiCard
            label="Incidents ouverts"
            value={open.length}
            icon={AlertTriangle}
            accent="bg-red-500/10 text-red-600 dark:text-red-400"
          />
          <KpiCard
            label="Retards"
            value={late.length}
            icon={Clock}
            accent="bg-amber-500/10 text-amber-600 dark:text-amber-400"
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {/* FLUX TEMPS RÉEL */}
          <Card className="lg:col-span-2">
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Flux temps réel</CardTitle>
              <Badge className="gap-1.5 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-emerald-500" />
                Live
              </Badge>
            </CardHeader>
            <CardContent className="space-y-2">
              {feed.length === 0 && (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Aucun événement aujourd'hui.
                </p>
              )}
              {feed.map((item) => (
                <div
                  key={item.key}
                  className="flex items-center gap-3 rounded-lg border bg-card/50 p-3"
                >
                  <span
                    className={
                      "h-2.5 w-2.5 shrink-0 rounded-full " +
                      (item.tone === "blue"
                        ? "bg-blue-500"
                        : item.tone === "green"
                          ? "bg-emerald-500"
                          : "bg-red-500")
                    }
                  />
                  <p className="text-sm font-medium">{item.property}</p>
                  <p className="ml-auto text-sm text-muted-foreground">
                    {item.text}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* ACTION PANEL */}
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Missions à attribuer</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {toAssign.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Tout est attribué 🎉
                  </p>
                )}
                {toAssign.slice(0, 4).map((t) => (
                  <div
                    key={t.id}
                    className="flex items-center justify-between gap-2 text-sm"
                  >
                    <span className="font-medium">{propName(t.propertyId)}</span>
                    <Badge className={TASK_STATUS_BADGE[t.status]}>
                      {TASK_STATUS_LABEL[t.status]}
                    </Badge>
                  </div>
                ))}
                <Link
                  href="/tasks"
                  className="mt-2 flex h-8 w-full items-center justify-center rounded-md border border-input bg-background px-3 text-xs font-medium hover:bg-accent"
                >
                  Ouvrir les missions
                </Link>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Prestataires disponibles</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {free.slice(0, 4).map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="font-medium">{p.name}</span>
                    <span className="text-muted-foreground">
                      {p.zone} · ★ {p.rating}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-center gap-2">
                <PlugZap className="h-4 w-4 text-muted-foreground" />
                <CardTitle>Synchronisation</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Calendriers Airbnb · Booking · Abritel synchronisés. WhatsApp
                Business connecté.
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </>
  );
}
