"use client";

import { MapPin, Phone, Star } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { isSameDay, minutesToLabel } from "@/lib/utils";
import { useStore } from "@/store/useStore";

export default function ProvidersPage() {
  const { providers, tasks } = useStore();
  const today = new Date();

  return (
    <>
      <Topbar title="Prestataires" />
      <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-3">
        {providers.map((provider) => {
          const todayTasks = tasks.filter(
            (t) =>
              t.providerId === provider.id && isSameDay(new Date(t.date), today),
          );
          const load = todayTasks.reduce((s, t) => s + t.estimatedTime, 0);

          return (
            <Card key={provider.id}>
              <CardContent className="space-y-3 p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                    {provider.name
                      .split(" ")
                      .map((n) => n[0])
                      .join("")
                      .slice(0, 2)}
                  </div>
                  <div>
                    <p className="font-semibold">{provider.name}</p>
                    <p className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                      {provider.rating} · note moyenne
                    </p>
                  </div>
                  <Badge
                    className={
                      "ml-auto " +
                      (provider.availabilityScore >= 0.7
                        ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400"
                        : provider.availabilityScore >= 0.5
                          ? "bg-amber-500/15 text-amber-600 dark:text-amber-400"
                          : "bg-muted text-muted-foreground")
                    }
                  >
                    {Math.round(provider.availabilityScore * 100)}% dispo
                  </Badge>
                </div>

                <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5" /> {provider.zone}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Phone className="h-3.5 w-3.5" /> {provider.phone}
                  </span>
                </div>

                <div className="rounded-lg bg-muted/50 p-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Charge aujourd'hui
                    </span>
                    <span className="font-medium">
                      {todayTasks.length} mission(s) · {minutesToLabel(load)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}
