"use client";

import { create } from "zustand";
import {
  cleaningTasks as seedTasks,
  incidents as seedIncidents,
  messages as seedMessages,
  properties,
  providers,
  reservations,
  users,
} from "@/lib/mock-data";
import type {
  CleaningTask,
  Incident,
  Message,
  TaskStatus,
} from "@/lib/types";
import { buildMissionMessage } from "@/lib/whatsapp";

interface StoreState {
  properties: typeof properties;
  reservations: typeof reservations;
  providers: typeof providers;
  users: typeof users;
  tasks: CleaningTask[];
  incidents: Incident[];
  messages: Message[];

  assignProvider: (taskId: string, providerId: string) => void;
  setTaskStatus: (taskId: string, status: TaskStatus) => void;
  acceptMission: (taskId: string) => void;
  resolveIncident: (incidentId: string) => void;
}

export const useStore = create<StoreState>((set) => ({
  properties,
  reservations,
  providers,
  users,
  tasks: seedTasks,
  incidents: seedIncidents,
  messages: seedMessages,

  assignProvider: (taskId, providerId) =>
    set((state) => {
      const task = state.tasks.find((t) => t.id === taskId);
      const provider = state.providers.find((p) => p.id === providerId);
      const property = task
        ? state.properties.find((p) => p.id === task.propertyId)
        : undefined;

      const tasks = state.tasks.map((t) =>
        t.id === taskId
          ? { ...t, providerId, status: "proposed" as TaskStatus }
          : t,
      );

      // Journalise le message WhatsApp automatique envoyé au prestataire.
      const messages =
        task && provider && property
          ? [
              ...state.messages,
              {
                id: `m${Date.now()}`,
                providerId,
                propertyId: property.id,
                taskId,
                direction: "out" as const,
                content: buildMissionMessage(property, task),
                mediaUrl: null,
                createdAt: new Date().toISOString(),
              },
            ]
          : state.messages;

      return { tasks, messages };
    }),

  setTaskStatus: (taskId, status) =>
    set((state) => ({
      tasks: state.tasks.map((t) => (t.id === taskId ? { ...t, status } : t)),
    })),

  acceptMission: (taskId) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === taskId ? { ...t, status: "accepted" as TaskStatus } : t,
      ),
    })),

  resolveIncident: (incidentId) =>
    set((state) => ({
      incidents: state.incidents.map((i) =>
        i.id === incidentId ? { ...i, status: "resolved" as const } : i,
      ),
    })),
}));
