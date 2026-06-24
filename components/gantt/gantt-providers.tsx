"use client";

import { useState } from "react";
import { GANTT_BAR_COLOR } from "@/lib/constants";
import type { CleaningTask, Property, Provider } from "@/lib/types";
import { cn, formatTime, isSameDay, minutesToLabel } from "@/lib/utils";

const DAY_START = 6;
const DAY_END = 22;
const HOURS = Array.from({ length: DAY_END - DAY_START + 1 }, (_, i) => DAY_START + i);

function pct(date: Date) {
  const h = date.getHours() + date.getMinutes() / 60;
  return ((Math.min(Math.max(h, DAY_START), DAY_END) - DAY_START) /
    (DAY_END - DAY_START)) *
    100;
}

// Gantt prestataires : 1 ligne par prestataire, réassignation par drag & drop.
export function GanttProviders({
  providers,
  tasks,
  properties,
  onReassign,
}: {
  providers: Provider[];
  tasks: CleaningTask[];
  properties: Property[];
  onReassign: (taskId: string, providerId: string) => void;
}) {
  const today = new Date();
  const [dragId, setDragId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);

  const propName = (id: string) =>
    properties.find((p) => p.id === id)?.name ?? "—";

  const dayTasks = tasks.filter((t) => isSameDay(new Date(t.date), today));

  return (
    <div className="overflow-x-auto scrollbar-thin">
      <div className="min-w-[760px]">
        <div className="flex border-b">
          <div className="w-44 shrink-0 px-3 py-2 text-xs font-medium text-muted-foreground">
            Prestataire
          </div>
          <div className="flex flex-1">
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

        {providers.map((provider) => {
          const provTasks = dayTasks.filter((t) => t.providerId === provider.id);
          const load = provTasks.reduce((s, t) => s + t.estimatedTime, 0);

          return (
            <div
              key={provider.id}
              onDragOver={(e) => {
                e.preventDefault();
                setOverId(provider.id);
              }}
              onDragLeave={() => setOverId((id) => (id === provider.id ? null : id))}
              onDrop={() => {
                if (dragId) onReassign(dragId, provider.id);
                setDragId(null);
                setOverId(null);
              }}
              className={cn(
                "flex items-stretch border-b transition-colors",
                overId === provider.id && "bg-primary/5",
              )}
            >
              <div className="flex w-44 shrink-0 flex-col justify-center px-3 py-3">
                <p className="truncate text-sm font-medium">{provider.name}</p>
                <p className="truncate text-[11px] text-muted-foreground">
                  {provider.zone} · charge {minutesToLabel(load)}
                </p>
              </div>

              <div className="relative flex-1">
                <div className="absolute inset-0 flex">
                  {HOURS.map((h) => (
                    <div key={h} className="flex-1 border-l" />
                  ))}
                </div>

                <div className="relative h-16">
                  {provTasks.map((task) => {
                    const left = pct(new Date(task.startTime));
                    const width = Math.max(pct(new Date(task.endTime)) - left, 8);
                    return (
                      <div
                        key={task.id}
                        draggable
                        onDragStart={() => setDragId(task.id)}
                        onDragEnd={() => {
                          setDragId(null);
                          setOverId(null);
                        }}
                        style={{ left: `${left}%`, width: `${width}%` }}
                        title={`${propName(task.propertyId)} · ${formatTime(task.startTime)}`}
                        className={cn(
                          "absolute top-1/2 z-10 flex h-9 -translate-y-1/2 cursor-grab items-center overflow-hidden rounded-md px-2 text-[11px] font-medium text-white shadow active:cursor-grabbing",
                          GANTT_BAR_COLOR[task.status],
                          dragId === task.id && "opacity-50",
                        )}
                      >
                        <span className="truncate">{propName(task.propertyId)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-3 px-3 text-xs text-muted-foreground">
        Glissez une mission vers un autre prestataire pour la réassigner et
        équilibrer les charges.
      </p>
    </div>
  );
}
