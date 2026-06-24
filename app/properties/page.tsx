"use client";

import { DoorClosed, Users } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Topbar } from "@/components/layout/topbar";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { availableWindow } from "@/lib/selectors";
import { minutesToLabel } from "@/lib/utils";
import { useStore } from "@/store/useStore";

export default function PropertiesPage() {
  const { properties, reservations, incidents } = useStore();

  return (
    <>
      <Topbar title="Logements" />
      <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-3">
        {properties.map((property) => {
          const win = availableWindow(property, reservations);
          const openInc = incidents.filter(
            (i) => i.propertyId === property.id && i.status !== "resolved",
          ).length;

          return (
            <Link key={property.id} href={`/properties/${property.id}`}>
              <Card className="group overflow-hidden transition-shadow hover:shadow-md">
                <div className="relative h-40 w-full overflow-hidden bg-muted">
                  <Image
                    src={property.photo}
                    alt={property.name}
                    fill
                    sizes="(max-width:768px) 100vw, 33vw"
                    className="object-cover transition-transform duration-300 group-hover:scale-105"
                  />
                  {openInc > 0 && (
                    <Badge className="absolute right-2 top-2 bg-red-600 text-white">
                      {openInc} incident{openInc > 1 ? "s" : ""}
                    </Badge>
                  )}
                </div>
                <div className="space-y-2 p-4">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold">{property.name}</p>
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Users className="h-3.5 w-3.5" />
                      {property.capacity}
                    </span>
                  </div>
                  <p className="truncate text-sm text-muted-foreground">
                    {property.address}
                  </p>
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <DoorClosed className="h-3.5 w-3.5" />
                      {property.doorCode}
                    </span>
                    <span>· Ménage {minutesToLabel(property.cleaningTime)}</span>
                  </div>
                  {win.departure && (
                    <Badge className="bg-blue-500/15 text-blue-600 dark:text-blue-400">
                      Départ aujourd'hui
                      {win.gapHours != null
                        ? ` · fenêtre ${Math.round(win.gapHours)}h`
                        : ""}
                    </Badge>
                  )}
                </div>
              </Card>
            </Link>
          );
        })}
      </div>
    </>
  );
}
