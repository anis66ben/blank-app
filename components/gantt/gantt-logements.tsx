"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { GANTT_BAR_COLOR, TASK_STATUS_LABEL } from "@/lib/constants";
import type { CleaningTask, Property, Reservation } from "@/lib/types";
import { cn, formatTime, isSameDay } from "@/lib/utils";

const DAY_START = 6;
const DAY_END = 22;
const HOURS = Array.from({ length: DAY_END - DAY_START + 1 }, (_, i) => DAY_START + i);

function pct(date: Date) {
  const h = date.getHours() + date.getMinutes() / 60;
  return ((Math.min(Math.max(h, DAY_START), DAY_END) - DAY_START) /
    (DAY_END - DAY_START)) *
    100;
}

export function GanttLogements({
  properties,
  tasks,
  reservations,
  providerName,
  onTaskClick,
}: {
  properties: Property[];
  tasks: CleaningTask[];
  reservations: Reservation[];
  providerName: (id: string | null) => string;
  onTaskClick?: (task: CleaningTask) => void;
}) {
  const today = new Date();
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div className="overflow-x-auto scrollbar-thin">
      <div className="min-w-[760px]">
        {/* En-tête des heures */}
        <div className="flex border-b">
          <div className="w-44 shrink-0 px-3 py-2 text-xs font-medium text-muted-foreground">
            Logement
          </div>
          <div className="relative flex-1">
            <div className="flex">
              {HOURS.map((h) => (
                <div
                  key={h}
                  className="flex-1 border-l py-2 text-center text-[11px] text-muted-foreground"
                >
                  {h}h
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Lignes : 1 logement = 1 ligne */}
        {properties.map((property) => {
          const occupiedToday = reservations.some(
            (r) =>
              r.propertyId === property.id &&
              new Date(r.startDate) <= today &&
              new Date(r.endDate) >= today &&
              !isSameDay(new Date(r.endDate), today),
          );
          const propTasks = tasks.filter(
            (t) => t.propertyId === property.id && isSameDay(new Date(t.date), today),
          );

          return (
            <div key={property.id} className="flex items-stretch border-b">
              <div className="flex w-44 shrink-0 flex-col justify-center px-3 py-3">
                <p className="truncate text-sm font-medium">{property.name}</p>
                <p className="truncate text-[11px] text-muted-foreground">
                  {property.address.split(",").pop()?.trim()}
                </p>
              </div>

              <div className="relative flex-1">
                {/* grille */}
                <div className="absolute inset-0 flex">
                  {HOURS.map((h) => (
                    <div key={h} className="flex-1 border-l" />
                  ))}
                </div>

                {/* occupation client (bleu) en fond si occupé toute la journée */}
                {occupiedToday && (
                  <div className="absolute inset-y-2 left-0 right-0 rounded-md bg-[hsl(var(--status-occupation))]/15" />
                )}

                {/* barres de missions */}
                <div className="relative h-16">
                  {propTasks.map((task) => {
                    const left = pct(new Date(task.startTime));
                    const width = Math.max(
                      pct(new Date(task.endTime)) - left,
                      6,
                    );
                    const key = task.id;
                    return (
                      <button
                        key={key}
                        onClick={() => onTaskClick?.(task)}
                        onMouseEnter={() => setHovered(key)}
                        onMouseLeave={() => setHovered(null)}
                        style={{ left: `${left}%`, width: `${width}%` }}
                        className={cn(
                          "absolute top-1/2 z-10 flex h-9 -translate-y-1/2 items-center gap-1.5 overflow-hidden rounded-md px-2 text-left text-[11px] font-medium text-white shadow transition-transform hover:scale-[1.02]",
                          GANTT_BAR_COLOR[task.status],
                        )}
                      >
                        <span className="truncate">
                          {providerName(task.providerId)}
                        </span>
                        {hovered === key && (
                          <span className="hidden truncate opacity-90 sm:inline">
                            · {formatTime(task.startTime)} ·{" "}
                            {TASK_STATUS_LABEL[task.status]}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Légende */}
      <div className="mt-4 flex flex-wrap gap-3 px-3 text-xs">
        {[
          ["Occupation client", "bg-[hsl(var(--status-occupation))]"],
          ["Mission proposée", "bg-[hsl(var(--status-proposed))]"],
          ["Mission acceptée", "bg-[hsl(var(--status-accepted))]"],
          ["Incident", "bg-[hsl(var(--status-incident))]"],
          ["Maintenance", "bg-[hsl(var(--status-maintenance))]"],
        ].map(([label, color]) => (
          <span key={label} className="flex items-center gap-1.5">
            <span className={cn("h-3 w-3 rounded-sm", color)} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
