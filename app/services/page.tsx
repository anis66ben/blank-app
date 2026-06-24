"use client";

import { Topbar } from "@/components/layout/topbar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  BILLING_UNIT_LABEL,
  INTERVENTION_STATUS_BADGE,
  INTERVENTION_STATUS_LABEL,
  SERVICE_CATEGORY_BADGE,
  SERVICE_CATEGORY_LABEL,
} from "@/lib/constants";
import { formatDate } from "@/lib/utils";
import { useStore } from "@/store/useStore";

export default function ServicesPage() {
  const { serviceTypes, interventions, properties, providers } = useStore();

  const propName = (id: string) => properties.find((p) => p.id === id)?.name ?? "—";
  const provName = (id: string) => providers.find((p) => p.id === id)?.name ?? "—";

  const recent = [...interventions]
    .sort((a, b) => +new Date(b.date) - +new Date(a.date))
    .slice(0, 20);

  return (
    <>
      <Topbar title="Catalogue de prestations" />
      <div className="space-y-6 p-5">
        {/* Catalogue ──────────────────────────────── */}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {serviceTypes.map((svc) => (
            <Card key={svc.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold">{svc.name}</p>
                    <p className="mt-1 text-2xl font-bold">
                      {svc.price.toLocaleString("fr-FR")} €
                      <span className="ml-1 text-sm font-normal text-muted-foreground">
                        / {BILLING_UNIT_LABEL[svc.unit]}
                      </span>
                    </p>
                  </div>
                  <Badge className={SERVICE_CATEGORY_BADGE[svc.category]}>
                    {SERVICE_CATEGORY_LABEL[svc.category]}
                  </Badge>
                </div>
                <div className="mt-3 text-xs text-muted-foreground">
                  {
                    interventions.filter(
                      (i) =>
                        i.serviceTypeId === svc.id &&
                        ["done", "invoiced"].includes(i.status),
                    ).length
                  }{" "}
                  intervention(s) réalisées
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Suivi des interventions ─────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Suivi des interventions</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="pb-2 pr-4">Logement</th>
                  <th className="pb-2 pr-4">Prestation</th>
                  <th className="pb-2 pr-4">Date</th>
                  <th className="pb-2 pr-4">Durée</th>
                  <th className="pb-2 pr-4">Intervenant</th>
                  <th className="pb-2 pr-4">Statut</th>
                  <th className="pb-2 text-right">Montant</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((iv) => {
                  const svc = serviceTypes.find((s) => s.id === iv.serviceTypeId);
                  return (
                    <tr key={iv.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-medium">
                        {propName(iv.propertyId)}
                      </td>
                      <td className="py-2 pr-4">
                        {svc && (
                          <Badge className={SERVICE_CATEGORY_BADGE[svc.category]}>
                            {svc.name}
                          </Badge>
                        )}
                      </td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        {formatDate(iv.date)}
                      </td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        {iv.durationMinutes} min
                      </td>
                      <td className="py-2 pr-4">{provName(iv.providerId)}</td>
                      <td className="py-2 pr-4">
                        <Badge className={INTERVENTION_STATUS_BADGE[iv.status]}>
                          {INTERVENTION_STATUS_LABEL[iv.status]}
                        </Badge>
                      </td>
                      <td className="py-2 text-right font-semibold">
                        {iv.amountBilled.toLocaleString("fr-FR")} €
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
