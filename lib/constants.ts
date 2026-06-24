import type {
  BillingUnit,
  IncidentSeverity,
  IncidentStatus,
  IncidentType,
  InterventionStatus,
  Platform,
  ServiceCategory,
  TaskPriority,
  TaskStatus,
} from "./types";

export const BILLING_UNIT_LABEL: Record<BillingUnit, string> = {
  heure: "Heure",
  forfait: "Forfait",
  intervention: "Intervention",
  nuitee: "Nuitée",
  logement: "Logement",
};

export const SERVICE_CATEGORY_LABEL: Record<ServiceCategory, string> = {
  menage: "Ménage",
  blanchisserie: "Blanchisserie",
  linge: "Location de linge",
  jardin: "Jardin / Extérieur",
  maintenance: "Maintenance",
  autre: "Autre",
};

export const SERVICE_CATEGORY_BADGE: Record<ServiceCategory, string> = {
  menage: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  blanchisserie: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
  linge: "bg-purple-500/15 text-purple-600 dark:text-purple-400",
  jardin: "bg-green-600/15 text-green-700 dark:text-green-400",
  maintenance: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  autre: "bg-muted text-muted-foreground",
};

export const INTERVENTION_STATUS_LABEL: Record<InterventionStatus, string> = {
  planned: "Planifiée",
  done: "Réalisée",
  invoiced: "Facturée",
  cancelled: "Annulée",
};

export const INTERVENTION_STATUS_BADGE: Record<InterventionStatus, string> = {
  planned: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  done: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  invoiced: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  cancelled: "bg-muted text-muted-foreground",
};

export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  todo: "À attribuer",
  proposed: "Proposé",
  accepted: "Accepté",
  in_progress: "En cours",
  quality_check: "Contrôle qualité",
  done: "Terminé",
  incident: "Incident",
};

// Classes Tailwind par statut (badges)
export const TASK_STATUS_BADGE: Record<TaskStatus, string> = {
  todo: "bg-muted text-muted-foreground",
  proposed: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
  accepted: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  in_progress: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
  quality_check: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
  done: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  incident: "bg-red-500/15 text-red-600 dark:text-red-400",
};

// Couleur de la barre Gantt par statut
export const GANTT_BAR_COLOR: Record<TaskStatus, string> = {
  todo: "bg-muted-foreground/40",
  proposed: "bg-[hsl(var(--status-proposed))]",
  accepted: "bg-[hsl(var(--status-accepted))]",
  in_progress: "bg-[hsl(var(--status-accepted))]",
  quality_check: "bg-[hsl(var(--status-maintenance))]",
  done: "bg-[hsl(var(--status-accepted))]",
  incident: "bg-[hsl(var(--status-incident))]",
};

export const PRIORITY_LABEL: Record<TaskPriority, string> = {
  low: "Faible",
  medium: "Moyen",
  high: "Urgent",
};

export const PRIORITY_BADGE: Record<TaskPriority, string> = {
  low: "bg-muted text-muted-foreground",
  medium: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  high: "bg-red-500/15 text-red-600 dark:text-red-400",
};

export const PLATFORM_LABEL: Record<Platform, string> = {
  airbnb: "Airbnb",
  booking: "Booking",
  abritel: "Abritel",
};

export const PLATFORM_BADGE: Record<Platform, string> = {
  airbnb: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
  booking: "bg-blue-600/15 text-blue-600 dark:text-blue-400",
  abritel: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
};

export const INCIDENT_TYPE_LABEL: Record<IncidentType, string> = {
  ampoule: "Ampoule cassée",
  fuite: "Fuite",
  television: "Télévision",
  vaisselle: "Vaisselle",
  degats_voyageur: "Dégâts voyageur",
};

export const INCIDENT_SEVERITY_LABEL: Record<IncidentSeverity, string> = {
  low: "Faible",
  medium: "Moyen",
  high: "Urgent",
};

export const INCIDENT_SEVERITY_BADGE: Record<IncidentSeverity, string> = {
  low: "bg-muted text-muted-foreground",
  medium: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  high: "bg-red-500/15 text-red-600 dark:text-red-400",
};

export const INCIDENT_STATUS_LABEL: Record<IncidentStatus, string> = {
  open: "Ouvert",
  in_progress: "En cours",
  resolved: "Résolu",
};

export const ROLE_LABEL = {
  admin: "Administrateur",
  manager: "Gestionnaire",
  provider: "Prestataire",
  owner: "Client propriétaire",
} as const;
