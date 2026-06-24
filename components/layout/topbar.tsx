"use client";

import { Bell, Search } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";

export function Topbar({ title }: { title: string }) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b bg-background/80 px-5 backdrop-blur">
      <h1 className="text-lg font-semibold">{title}</h1>
      <div className="ml-auto flex items-center gap-2">
        <div className="hidden items-center gap-2 rounded-md border bg-card px-3 py-1.5 text-sm text-muted-foreground sm:flex">
          <Search className="h-4 w-4" />
          <span>Rechercher…</span>
        </div>
        <button
          className="relative inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-accent"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500" />
        </button>
        <ThemeToggle />
      </div>
    </header>
  );
}
