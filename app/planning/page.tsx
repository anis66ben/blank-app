"use client";

import { useState } from "react";
import { Topbar } from "@/components/layout/topbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GanttLogements } from "@/components/gantt/gantt-logements";
import { GanttProviders } from "@/components/gantt/gantt-providers";
import {
  PRIORITY_LABEL,
  TASK_STATUS_BADGE,
  TASK_STATUS_LABEL,
} from "@/lib/constants";
import type { CleaningTask } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { cn, formatDateLong, formatTime } from "@/lib/utils";
import { useStore } from "@/store/useStore";

type View = "properties" | "providers";
type Zoom = "day" | "week" | "month";

export default function PlanningPage() {
  const { properties, tasks, reservations, providers, assignProvider } =
    useStore();
  const [view, setView] = useState<View>("properties");
  const [zoom, setZoom] = useState<Zoom>("day");
  const [selected, setSelected] = useState<CleaningTask | null>(null);

  const providerName = (id: string | null) =>
    id ? (providers.find((p) => p.id === id)?.name ?? "—") : "À attribuer";

  return (
    <>
      <Topbar title="Planning Gantt" />
      <div className="space-y-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex gap-2">
            <Tab active={view === "properties"} onClick={() => setView("properties")}>
              Logements
            </Tab>
            <Tab active={view === "providers"} onClick={() => setView("providers")}>
              Prestataires
            </Tab>
          </div>
          <div className="flex items-center gap-3">
            <p className="text-sm text-muted-foreground">
              {formatDateLong(new Date().toISOString())}
            </p>
            <div className="flex rounded-md border p-0.5">
              {(["day", "week", "month"] as Zoom[]).map((z) => (
                <button
                  key={z}
                  onClick={() => setZoom(z)}
                  className={cn(
                    "rounded px-3 py-1 text-xs font-medium capitalize",
                    zoom === z
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {z === "day" ? "Jour" : z === "week" ? "Semaine" : "Mois"}
                </button>
              ))}
            </div>
          </div>
        </div>

        <Card>
          <CardContent className="p-3">
            {view === "properties" ? (
              <GanttLogements
                properties={properties}
                tasks={tasks}
                reservations={reservations}
                providerName={providerName}
                onTaskClick={setSelected}
              />
            ) : (
              <GanttProviders
                providers={providers}
                tasks={tasks}
                properties={properties}
                onReassign={assignProvider}
              />
            )}
          </CardContent>
        </Card>

        {/* Détail mission (clic sur une barre) */}
        {selected && (
          <Card className="animate-fade-in">
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>
                {properties.find((p) => p.id === selected.propertyId)?.name}
              </CardTitle>
              <button
                onClick={() => setSelected(null)}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                Fermer
              </button>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-4 text-sm">
              <span>
                🕒 {formatTime(selected.startTime)} – {formatTime(selected.endTime)}
              </span>
              <span>👤 {providerName(selected.providerId)}</span>
              <Badge className={TASK_STATUS_BADGE[selected.status]}>
                {TASK_STATUS_LABEL[selected.status]}
              </Badge>
              <span>Priorité : {PRIORITY_LABEL[selected.priority]}</span>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}

function Tab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-md px-4 py-1.5 text-sm font-medium transition-colors",
        active
          ? "bg-primary text-primary-foreground"
          : "bg-secondary text-secondary-foreground hover:bg-accent",
      )}
    >
      {children}
    </button>
  );
}
