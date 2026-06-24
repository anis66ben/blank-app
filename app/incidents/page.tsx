"use client";

import { AlertTriangle } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  INCIDENT_SEVERITY_BADGE,
  INCIDENT_SEVERITY_LABEL,
  INCIDENT_STATUS_LABEL,
  INCIDENT_TYPE_LABEL,
} from "@/lib/constants";
import { formatDate, formatTime } from "@/lib/utils";
import { useStore } from "@/store/useStore";

export default function IncidentsPage() {
  const { incidents, properties, resolveIncident } = useStore();
  const propName = (id: string) =>
    properties.find((p) => p.id === id)?.name ?? "—";

  const sorted = [...incidents].sort((a, b) => {
    const rank = { open: 0, in_progress: 1, resolved: 2 };
    return rank[a.status] - rank[b.status];
  });

  return (
    <>
      <Topbar title="Incidents" />
      <div className="space-y-3 p-5">
        {sorted.map((i) => (
          <Card key={i.id}>
            <CardContent className="flex flex-wrap items-center gap-3 p-4">
              <div
                className={
                  "flex h-9 w-9 items-center justify-center rounded-lg " +
                  (i.severity === "high"
                    ? "bg-red-500/15 text-red-600 dark:text-red-400"
                    : "bg-amber-500/15 text-amber-600 dark:text-amber-400")
                }
              >
                <AlertTriangle className="h-4 w-4" />
              </div>
              <div className="min-w-[160px]">
                <p className="font-medium">{INCIDENT_TYPE_LABEL[i.type]}</p>
                <p className="text-xs text-muted-foreground">
                  {propName(i.propertyId)} · {formatDate(i.createdAt)}{" "}
                  {formatTime(i.createdAt)}
                </p>
              </div>
              <Badge className={INCIDENT_SEVERITY_BADGE[i.severity]}>
                {INCIDENT_SEVERITY_LABEL[i.severity]}
              </Badge>
              <span className="text-sm text-muted-foreground">
                {i.description}
              </span>
              <div className="ml-auto flex items-center gap-3">
                <span className="text-xs text-muted-foreground">
                  {INCIDENT_STATUS_LABEL[i.status]}
                </span>
                {i.status !== "resolved" && (
                  <Button size="sm" variant="outline" onClick={() => resolveIncident(i.id)}>
                    Résoudre
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
