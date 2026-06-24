"use client";

import {
  AlertTriangle,
  BarChart3,
  Building2,
  CalendarRange,
  ConciergeBell,
  LayoutDashboard,
  ListChecks,
  Users,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Tour de contrôle", icon: LayoutDashboard },
  { href: "/planning", label: "Planning Gantt", icon: CalendarRange },
  { href: "/tasks", label: "Missions ménage", icon: ListChecks },
  { href: "/properties", label: "Logements", icon: Building2 },
  { href: "/providers", label: "Prestataires", icon: Users },
  { href: "/incidents", label: "Incidents", icon: AlertTriangle },
  { href: "/activity", label: "Activité & Revenus", icon: BarChart3 },
  { href: "/services", label: "Catalogue prestations", icon: ConciergeBell },
  { href: "/assistant", label: "IA & Assistant", icon: Zap },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-64 shrink-0 border-r bg-card/40 md:flex md:flex-col">
      <div className="flex h-16 items-center gap-2 border-b px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Zap className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight">Concierge Flow</p>
          <p className="text-[11px] text-muted-foreground">Tour de contrôle</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {nav.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary text-sm font-semibold">
            CM
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">Camille Moreau</p>
            <p className="truncate text-xs text-muted-foreground">
              Administrateur
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
