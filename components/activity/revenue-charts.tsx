/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DaySeries, ProviderCost, PropertyProfit, ServiceShare } from "@/lib/financials";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CHART_COLORS = [
  "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899",
];

function fmt(v: number) {
  return `${v.toLocaleString("fr-FR")} €`;
}

export function RevenueChart({ data }: { data: DaySeries[] }) {
  const visible = data.filter((_, i) => i % 2 === 0 || data.length <= 15);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Évolution CA & Bénéfice (30 jours)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={visible} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="caGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10 }}
              tickLine={false}
              interval={4}
              className="text-muted-foreground"
            />
            <YAxis
              tickFormatter={(v) => `${v}€`}
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(v: any, name: any) => [fmt(Number(v)), name === "ca" ? "CA" : "Bénéfice"]}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <Area
              type="monotone"
              dataKey="ca"
              stroke="#6366f1"
              fill="url(#caGrad)"
              strokeWidth={2}
              name="CA"
            />
            <Area
              type="monotone"
              dataKey="profit"
              stroke="#10b981"
              fill="url(#profitGrad)"
              strokeWidth={2}
              name="Bénéfice"
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function ServiceShareChart({ data }: { data: ServiceShare[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>CA par type de prestation</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              dataKey="ca"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={80}
              label={(p: any) =>
                `${(p.name as string).split(" ")[0]} ${Math.round((p.percent as number) * 100)}%`
              }
              labelLine={false}
            >
              {data.map((_, idx) => (
                <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(v: any) => [fmt(Number(v)), "CA"]}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function ProviderCostChart({ data }: { data: ProviderCost[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Coûts main-d'œuvre par prestataire</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              tickFormatter={(v: string) => v.split(" ")[0]}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => `${v}€`}
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(v: any, name: any) => [
                name === "cost" ? fmt(Number(v)) : `${v}h`,
                name === "cost" ? "Coût MO" : "Heures",
              ]}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <Bar dataKey="cost" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Coût MO" />
            <Bar dataKey="hours" fill="#6366f1" radius={[4, 4, 0, 0]} name="Heures" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function PropertyProfitChart({ data }: { data: PropertyProfit[] }) {
  const top6 = data.slice(0, 6);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Bénéfice par logement</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={top6} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              tickFormatter={(v: string) => v.split(" ").slice(-1)[0]}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => `${v}€`}
              tick={{ fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(v: any, name: any) => [
                fmt(Number(v)),
                name === "ca" ? "CA" : name === "cost" ? "Coût MO" : "Bénéfice",
              ]}
              contentStyle={{ fontSize: 12, borderRadius: 8 }}
            />
            <Legend
              formatter={(v: string) =>
                v === "ca" ? "CA" : v === "cost" ? "Coût MO" : "Bénéfice"
              }
              wrapperStyle={{ fontSize: 11 }}
            />
            <Bar dataKey="ca" fill="#6366f1" radius={[4, 4, 0, 0]} name="ca" />
            <Bar dataKey="cost" fill="#f59e0b" radius={[4, 4, 0, 0]} name="cost" />
            <Bar dataKey="profit" fill="#10b981" radius={[4, 4, 0, 0]} name="profit" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
