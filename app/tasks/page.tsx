"use client";

import { useMemo, useState } from "react";
import { Topbar } from "@/components/layout/topbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  PRIORITY_BADGE,
  PRIORITY_LABEL,
  TASK_STATUS_BADGE,
  TASK_STATUS_LABEL,
} from "@/lib/constants";
import { scoreProviders } from "@/lib/assignment";
import type { TaskStatus } from "@/lib/types";
import { cn, formatTime, isSameDay, minutesToLabel } from "@/lib/utils";
import { useStore } from "@/store/useStore";

type Filter = "today" | "tomorrow" | "late" | "urgent" | "all";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "today", label: "Aujourd'hui" },
  { key: "tomorrow", label: "Demain" },
  { key: "late", label: "En retard" },
  { key: "urgent", label: "Urgents" },
  { key: "all", label: "Toutes" },
];

const NEXT_STATUS: Partial<Record<TaskStatus, TaskStatus>> = {
  accepted: "in_progress",
  in_progress: "quality_check",
  quality_check: "done",
};

export default function TasksPage() {
  const { tasks, properties, providers, assignProvider, setTaskStatus } =
    useStore();
  const [filter, setFilter] = useState<Filter>("today");
  const [assigning, setAssigning] = useState<string | null>(null);

  const property = (id: string) => properties.find((p) => p.id === id);

  const filtered = useMemo(() => {
    const now = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tasks
      .filter((t) => {
        switch (filter) {
          case "today":
            return isSameDay(new Date(t.date), now);
          case "tomorrow":
            return isSameDay(new Date(t.date), tomorrow);
          case "late":
            return t.status !== "done" && new Date(t.endTime) < now;
          case "urgent":
            return t.priority === "high";
          default:
            return true;
        }
      })
      .sort((a, b) => +new Date(a.startTime) - +new Date(b.startTime));
  }, [tasks, filter]);

  return (
    <>
      <Topbar title="Missions ménage" />
      <div className="space-y-4 p-5">
        {/* FILTRES */}
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={cn(
                "rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
                filter === f.key
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-accent",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* LISTE MISSIONS */}
        <Card className="divide-y">
          {filtered.length === 0 && (
            <p className="p-8 text-center text-sm text-muted-foreground">
              Aucune mission pour ce filtre.
            </p>
          )}
          {filtered.map((task) => {
            const prop = property(task.propertyId);
            const provider = providers.find((p) => p.id === task.providerId);
            const next = NEXT_STATUS[task.status];
            const ranked = prop ? scoreProviders(prop, providers) : [];

            return (
              <div key={task.id} className="p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="min-w-[140px]">
                    <p className="font-medium">{prop?.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatTime(task.startTime)} – {formatTime(task.endTime)} ·{" "}
                      {minutesToLabel(task.estimatedTime)}
                    </p>
                  </div>

                  <Badge className={PRIORITY_BADGE[task.priority]}>
                    {PRIORITY_LABEL[task.priority]}
                  </Badge>
                  <Badge className={TASK_STATUS_BADGE[task.status]}>
                    {TASK_STATUS_LABEL[task.status]}
                  </Badge>

                  <span className="text-sm text-muted-foreground">
                    {provider ? `👤 ${provider.name}` : "Non attribué"}
                  </span>

                  <div className="ml-auto flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setAssigning(assigning === task.id ? null : task.id)
                      }
                    >
                      {provider ? "Réattribuer" : "Attribuer"}
                    </Button>
                    {next && (
                      <Button
                        size="sm"
                        onClick={() => setTaskStatus(task.id, next)}
                      >
                        → {TASK_STATUS_LABEL[next]}
                      </Button>
                    )}
                  </div>
                </div>

                {/* Panneau d'attribution automatique (score MVP) */}
                {assigning === task.id && (
                  <div className="mt-3 rounded-lg border bg-muted/40 p-3">
                    <p className="mb-2 text-xs font-medium text-muted-foreground">
                      Proposition automatique (disponibilité 40% · zone 30% ·
                      note 20% · charge 10%) — un message WhatsApp est envoyé à
                      la sélection.
                    </p>
                    <div className="space-y-1.5">
                      {ranked.map(({ provider: pr, score }, idx) => (
                        <div
                          key={pr.id}
                          className="flex items-center gap-3 rounded-md bg-card px-3 py-2 text-sm"
                        >
                          {idx === 0 && (
                            <Badge className="bg-primary/15 text-primary">
                              Recommandé
                            </Badge>
                          )}
                          <span className="font-medium">{pr.name}</span>
                          <span className="text-xs text-muted-foreground">
                            {pr.zone} · ★ {pr.rating} · {pr.currentLoad} mission(s)
                          </span>
                          <span className="ml-auto text-xs font-semibold">
                            {Math.round(score * 100)}%
                          </span>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              assignProvider(task.id, pr.id);
                              setAssigning(null);
                            }}
                          >
                            Envoyer
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </Card>
      </div>
    </>
  );
}
