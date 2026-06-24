// Modèle de données Concierge Flow (aligné sur le schéma Supabase du cahier des charges)

export type UserRole = "admin" | "manager" | "provider" | "owner";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  phone: string;
}

export interface Property {
  id: string;
  name: string;
  address: string;
  capacity: number;
  cleaningTime: number; // minutes
  qualityCheckTime: number; // minutes
  doorCode: string;
  notes: string;
  lat: number;
  lng: number;
  photo: string;
  ownerId: string;
}

export type Platform = "airbnb" | "booking" | "abritel";

export interface Reservation {
  id: string;
  propertyId: string;
  platform: Platform;
  guestName: string;
  startDate: string; // ISO
  endDate: string; // ISO
  guestsCount: number;
}

export type TaskStatus =
  | "todo" // À attribuer
  | "proposed" // Proposé
  | "accepted" // Accepté
  | "in_progress" // En cours
  | "quality_check" // Contrôle qualité
  | "done" // Terminé
  | "incident"; // Incident

export type TaskPriority = "low" | "medium" | "high";

export interface CleaningTask {
  id: string;
  propertyId: string;
  reservationId: string | null;
  providerId: string | null;
  date: string; // ISO date
  startTime: string; // ISO datetime
  endTime: string; // ISO datetime
  status: TaskStatus;
  priority: TaskPriority;
  estimatedTime: number; // minutes
}

export interface Provider {
  id: string;
  name: string;
  phone: string;
  zone: string;
  rating: number; // 0..5
  availabilityScore: number; // 0..1
  currentLoad: number; // nb de missions du jour
}

export type IncidentType =
  | "ampoule"
  | "fuite"
  | "television"
  | "vaisselle"
  | "degats_voyageur";

export type IncidentSeverity = "low" | "medium" | "high";
export type IncidentStatus = "open" | "in_progress" | "resolved";

export interface Incident {
  id: string;
  propertyId: string;
  taskId: string | null;
  type: IncidentType;
  severity: IncidentSeverity;
  description: string;
  status: IncidentStatus;
  createdAt: string;
}

export type MessageDirection = "in" | "out";

export interface Message {
  id: string;
  providerId: string | null;
  propertyId: string | null;
  taskId: string | null;
  direction: MessageDirection;
  content: string;
  mediaUrl: string | null;
  createdAt: string;
}
