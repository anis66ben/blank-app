"use client";

import {
  ArrowUpRight,
  BadgeEuro,
  BarChart3,
  CalendarCheck,
  TrendingUp,
  Users,
} from "lucide-react";
import { useMemo } from "react";
import { Topbar } from "@/components/layout/topbar";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ProviderCostChart,
  PropertyProfitChart,
  RevenueChart,
  ServiceShareChart,
} from "@/components/activity/revenue-charts";
import {
  INTERVENTION_STATUS_BADGE,
  INTERVENTION_STATUS_LABEL,
  SERVICE_CATEGORY_BADGE,
  SERVICE_CATEGORY_LABEL,
} from "@/lib/constants";
import {
  buildDailySeries,
  computeKPIs,
  costByProvider,
  profitByProperty,
  revenueByService,
} from "@/lib/financials";
import { formatDate } from "@/lib/utils";
import { useStore } from "@/store/useStore";

function euros(n: number) {
  return n.toLocaleString("fr-FR") + " €";
}

export default function ActivityPage() {
  const { interventions, providers, properties, serviceTypes } = useStore();

  const kpis = useMemo(
    () => computeKPIs(interventions, providers),
    [interventions, providers],
  );
  const dailySeries = useMemo(
    () => buildDailySeries(interventions, providers),
    [interventions, providers],
  );
  const serviceShares = useMemo(
    () => revenueByService(interventions, serviceTypes),
    [interventions, serviceTypes],
  );
  const providerCosts = useMemo(
    () => costByProvider(interventions, providers),
    [interventions, providers],
  );
  const propProfits = useMemo(() => {
    const nameMap = new Map(properties.map((p) => [p.id, p.name]));
    return profitByProperty(interventions, providers, nameMap);
  }, [interventions, providers, properties]);

  const propName = (id: string) => properties.find((p) => p.id === id)?.name ?? "—";
  const svcName = (id: string) => serviceTypes.find((s) => s.id === id)?.name ?? "—";
  const svcCat = (id: string) => serviceTypes.find((s) => s.id === id)?.category ?? "autre";

  const recent = [...interventions]
    .sort((a, b) => +new Date(b.date) - +new Date(a.date))
    .slice(0, 8);

  return (
    <>
      <Topbar title="Activité & Rentabilité" />
      <div className="space-y-6 p-5">
        {/* KPI CA ────────────────────────────────── */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <KpiCard
            label="CA Aujourd'hui"
            value={euros(kpis.caDay)}
            icon={BadgeEuro}
            accent="bg-primary/10 text-primary"
          />
          <KpiCard
            label="CA Semaine"
            value={euros(kpis.caWeek)}
            icon={CalendarCheck}
            accent="bg-blue-500/10 text-blue-600 dark:text-blue-400"
          />
          <KpiCard
            label="CA Mois"
            value={euros(kpis.caMonth)}
            icon={BarChart3}
            accent="bg-violet-500/10 text-violet-600 dark:text-violet-400"
          />
          <KpiCard
            label="CA Année"
            value={euros(kpis.caYear)}
            icon={TrendingUp}
            accent="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
          />
        </div>

        {/* KPI Rentabilité ───────────────────────── */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Card className="p-5">
            <p className="text-sm text-muted-foreground">CA Réalisé (total)</p>
            <p className="mt-2 text-2xl font-semibold">{euros(kpis.caRealised)}</p>
          </Card>
          <Card className="p-5">
            <p className="text-sm text-muted-foreground">CA Prévisionnel</p>
            <p className="mt-2 text-2xl font-semibold text-amber-600">
              {euros(kpis.caForecast)}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">missions planifiées</p>
          </Card>
          <Card className="p-5">
            <p className="text-sm text-muted-foreground">Coût main-d'œuvre</p>
            <p className="mt-2 text-2xl font-semibold text-red-600">
              {euros(kpis.labourCostTotal)}
            </p>
          </Card>
          <Card className="p-5">
            <p className="text-sm text-muted-foreground">Bénéfice brut</p>
            <p className="mt-2 text-2xl font-semibold text-emerald-600">
              {euros(kpis.grossProfit)}
            </p>
            <div className="mt-1 flex items-center gap-1 text-xs text-emerald-600">
              <ArrowUpRight className="h-3.5 w-3.5" />
              Marge {kpis.grossMarginPct}%
            </div>
          </Card>
        </div>

        {/* Graphiques ligne 1 ─────────────────────── */}
        <div className="grid gap-4 lg:grid-cols-2">
          <RevenueChart data={dailySeries} />
          <ServiceShareChart data={serviceShares} />
        </div>

        {/* Graphiques ligne 2 ─────────────────────── */}
        <div className="grid gap-4 lg:grid-cols-2">
          <ProviderCostChart data={providerCosts} />
          <PropertyProfitChart data={propProfits} />
        </div>

        {/* Résumé prestataires ────────────────────── */}
        <Card>
          <CardHeader className="flex-row items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <CardTitle>Synthèse intervenants</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="pb-2 pr-4">Intervenant</th>
                  <th className="pb-2 pr-4">Taux horaire</th>
                  <th className="pb-2 pr-4">Heures</th>
                  <th className="pb-2 pr-4">Coût MO</th>
                  <th className="pb-2">Interventions</th>
                </tr>
              </thead>
              <tbody>
                {providerCosts.map((pc) => {
                  const pr = providers.find((p) => p.name === pc.name);
                  return (
                    <tr key={pc.name} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-medium">{pc.name}</td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        {pr?.hourlyRate} €/h
                      </td>
                      <td className="py-2 pr-4">{pc.hours}h</td>
                      <td className="py-2 pr-4 text-amber-600">
                        {pc.cost.toLocaleString("fr-FR")} €
                      </td>
                      <td className="py-2">{pc.interventions}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>

        {/* Interventions récentes ─────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle>Interventions récentes</CardTitle>
          </CardHeader>
          <CardContent className="divide-y">
            {recent.map((iv) => (
              <div
                key={iv.id}
                className="flex flex-wrap items-center gap-3 py-3 text-sm"
              >
                <span className="font-medium">{propName(iv.propertyId)}</span>
                <Badge className={SERVICE_CATEGORY_BADGE[svcCat(iv.serviceTypeId)]}>
                  {SERVICE_CATEGORY_LABEL[svcCat(iv.serviceTypeId)]}
                </Badge>
                <span className="text-muted-foreground">{svcName(iv.serviceTypeId)}</span>
                <span className="text-muted-foreground">{formatDate(iv.date)}</span>
                <span className="text-muted-foreground">{iv.durationMinutes} min</span>
                <Badge className={INTERVENTION_STATUS_BADGE[iv.status]}>
                  {INTERVENTION_STATUS_LABEL[iv.status]}
                </Badge>
                <span className="ml-auto font-semibold">
                  {iv.amountBilled.toLocaleString("fr-FR")} €
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
