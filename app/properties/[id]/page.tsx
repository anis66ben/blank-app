"use client";

import { ArrowLeft, DoorClosed, MapPin, Users } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { useState } from "react";
import { Topbar } from "@/components/layout/topbar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  INCIDENT_SEVERITY_BADGE,
  INCIDENT_SEVERITY_LABEL,
  INCIDENT_STATUS_LABEL,
  INCIDENT_TYPE_LABEL,
  PLATFORM_BADGE,
  PLATFORM_LABEL,
  TASK_STATUS_BADGE,
  TASK_STATUS_LABEL,
} from "@/lib/constants";
import { cn, formatDate, formatTime, minutesToLabel } from "@/lib/utils";
import { useStore } from "@/store/useStore";

const TABS = [
  "Calendrier",
  "Missions",
  "WhatsApp",
  "Photos",
  "Incidents",
] as const;
type Tab = (typeof TABS)[number];

export default function PropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const { properties, reservations, tasks, incidents, messages, providers } =
    useStore();
  const [tab, setTab] = useState<Tab>("Calendrier");

  const property = properties.find((p) => p.id === params.id);
  if (!property) return notFound();

  const propRes = reservations
    .filter((r) => r.propertyId === property.id)
    .sort((a, b) => +new Date(a.startDate) - +new Date(b.startDate));
  const propTasks = tasks.filter((t) => t.propertyId === property.id);
  const propInc = incidents.filter((i) => i.propertyId === property.id);
  const propMsg = messages.filter((m) => m.propertyId === property.id);
  const photos = propMsg.filter((m) => m.mediaUrl);
  const providerName = (id: string | null) =>
    id ? (providers.find((p) => p.id === id)?.name ?? "—") : "Non attribué";

  return (
    <>
      <Topbar title={property.name} />
      <div className="space-y-5 p-5">
        <Link
          href="/properties"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Logements
        </Link>

        {/* En-tête avec photo */}
        <Card className="overflow-hidden">
          <div className="relative h-52 w-full bg-muted">
            <Image
              src={property.photo}
              alt={property.name}
              fill
              sizes="100vw"
              className="object-cover"
            />
          </div>
          <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-2 p-5">
            <h2 className="text-xl font-semibold">{property.name}</h2>
            <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <MapPin className="h-4 w-4" /> {property.address}
            </span>
            <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <DoorClosed className="h-4 w-4" /> Code {property.doorCode}
            </span>
            <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Users className="h-4 w-4" /> {property.capacity} pers.
            </span>
            <span className="text-sm text-muted-foreground">
              Ménage {minutesToLabel(property.cleaningTime)} · Contrôle{" "}
              {minutesToLabel(property.qualityCheckTime)}
            </span>
          </CardContent>
        </Card>

        {/* Onglets */}
        <div className="flex flex-wrap gap-1 border-b">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors",
                tab === t
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Contenu */}
        {tab === "Calendrier" && (
          <div className="space-y-2">
            {propRes.map((r) => (
              <Card key={r.id}>
                <CardContent className="flex flex-wrap items-center gap-3 p-4">
                  <Badge className={PLATFORM_BADGE[r.platform]}>
                    {PLATFORM_LABEL[r.platform]}
                  </Badge>
                  <span className="font-medium">{r.guestName}</span>
                  <span className="text-sm text-muted-foreground">
                    {formatDate(r.startDate)} → {formatDate(r.endDate)}
                  </span>
                  <span className="ml-auto text-sm text-muted-foreground">
                    {r.guestsCount} voyageurs
                  </span>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {tab === "Missions" && (
          <div className="space-y-2">
            {propTasks.map((t) => (
              <Card key={t.id}>
                <CardContent className="flex flex-wrap items-center gap-3 p-4">
                  <span className="text-sm">{formatDate(t.date)}</span>
                  <span className="text-sm text-muted-foreground">
                    {formatTime(t.startTime)} – {formatTime(t.endTime)}
                  </span>
                  <span className="text-sm">👤 {providerName(t.providerId)}</span>
                  <Badge className={cn("ml-auto", TASK_STATUS_BADGE[t.status])}>
                    {TASK_STATUS_LABEL[t.status]}
                  </Badge>
                </CardContent>
              </Card>
            ))}
            {propTasks.length === 0 && (
              <p className="text-sm text-muted-foreground">Aucune mission.</p>
            )}
          </div>
        )}

        {tab === "WhatsApp" && (
          <Card>
            <CardContent className="space-y-3 p-4">
              {propMsg.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Aucune conversation.
                </p>
              )}
              {propMsg.map((m) => (
                <div
                  key={m.id}
                  className={cn(
                    "max-w-[80%] rounded-2xl px-4 py-2 text-sm",
                    m.direction === "out"
                      ? "ml-auto bg-primary text-primary-foreground"
                      : "bg-secondary",
                  )}
                >
                  <p className="whitespace-pre-line">{m.content}</p>
                  {m.mediaUrl && (
                    <div className="relative mt-2 h-32 w-48 overflow-hidden rounded-lg">
                      <Image
                        src={m.mediaUrl}
                        alt="media"
                        fill
                        sizes="200px"
                        className="object-cover"
                      />
                    </div>
                  )}
                  <p className="mt-1 text-[10px] opacity-70">
                    {formatTime(m.createdAt)}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {tab === "Photos" && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {photos.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Aucune photo avant/après.
              </p>
            )}
            {photos.map((m) => (
              <div
                key={m.id}
                className="relative aspect-square overflow-hidden rounded-lg bg-muted"
              >
                <Image
                  src={m.mediaUrl!}
                  alt="photo ménage"
                  fill
                  sizes="200px"
                  className="object-cover"
                />
              </div>
            ))}
          </div>
        )}

        {tab === "Incidents" && (
          <div className="space-y-2">
            {propInc.length === 0 && (
              <p className="text-sm text-muted-foreground">Aucun incident.</p>
            )}
            {propInc.map((i) => (
              <Card key={i.id}>
                <CardContent className="flex flex-wrap items-center gap-3 p-4">
                  <span className="font-medium">
                    {INCIDENT_TYPE_LABEL[i.type]}
                  </span>
                  <Badge className={INCIDENT_SEVERITY_BADGE[i.severity]}>
                    {INCIDENT_SEVERITY_LABEL[i.severity]}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {i.description}
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {INCIDENT_STATUS_LABEL[i.status]}
                  </span>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
