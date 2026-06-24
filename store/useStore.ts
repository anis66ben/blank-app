"use client";

import { create } from "zustand";
import {
  cleaningTasks as seedTasks,
  incidents as seedIncidents,
  interventions as seedInterventions,
  messages as seedMessages,
  properties,
  providers,
  reservations,
  serviceTypes,
  users,
} from "@/lib/mock-data";
import type {
  CleaningTask,
  Incident,
  Intervention,
  ProcessedMessage,
  TaskStatus,
} from "@/lib/types";
import { buildMissionMessage } from "@/lib/whatsapp";
import { processMessage } from "@/lib/ai-processor";

interface StoreState {
  properties: typeof properties;
  reservations: typeof reservations;
  providers: typeof providers;
  users: typeof users;
  serviceTypes: typeof serviceTypes;
  tasks: CleaningTask[];
  incidents: Incident[];
  interventions: Intervention[];
  messages: typeof seedMessages;

  // Missions
  assignProvider: (taskId: string, providerId: string) => void;
  setTaskStatus: (taskId: string, status: TaskStatus) => void;
  acceptMission: (taskId: string) => void;

  // Incidents
  resolveIncident: (incidentId: string) => void;

  // Interventions (module activité)
  addIntervention: (intervention: Intervention) => void;
  updateInterventionStatus: (id: string, status: Intervention["status"]) => void;

  // IA opérationnelle : applique les actions extraites d'un message
  applyAIMessage: (text: string) => ProcessedMessage;
}

export const useStore = create<StoreState>((set, get) => ({
  properties,
  reservations,
  providers,
  users,
  serviceTypes,
  tasks: seedTasks,
  incidents: seedIncidents,
  interventions: seedInterventions,
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

  addIntervention: (intervention) =>
    set((state) => ({
      interventions: [...state.interventions, intervention],
    })),

  updateInterventionStatus: (id, status) =>
    set((state) => ({
      interventions: state.interventions.map((i) =>
        i.id === id ? { ...i, status } : i,
      ),
    })),

  applyAIMessage: (text) => {
    const state = get();
    const result = processMessage(text, {
      properties: state.properties,
      providers: state.providers,
      serviceTypes: state.serviceTypes,
      tasks: state.tasks,
      interventions: state.interventions,
    });

    // Appliquer chaque action au store
    set((s) => {
      let tasks = [...s.tasks];
      let incidents = [...s.incidents];
      let interventions = [...s.interventions];
      let messages = [...s.messages];

      // Log du message entrant
      messages = [
        ...messages,
        {
          id: `m_ai_${Date.now()}`,
          providerId: null,
          propertyId:
            s.properties.find((p) => p.name === result.detectedProperty)?.id ??
            null,
          taskId: null,
          direction: "in" as const,
          content: text,
          mediaUrl: null,
          createdAt: new Date().toISOString(),
        },
      ];

      result.actions.forEach((action) => {
        if (action.type === "update_task") {
          const { taskId, status, endTime } = action.payload as {
            taskId: string;
            status: TaskStatus;
            endTime?: string;
          };
          tasks = tasks.map((t) =>
            t.id === taskId
              ? { ...t, status, endTime: endTime ?? t.endTime }
              : t,
          );
        }

        if (action.type === "create_intervention") {
          const p = action.payload as Partial<Intervention>;
          interventions = [
            ...interventions,
            {
              id: `iv_ai_${Date.now()}_${Math.random().toString(36).slice(2)}`,
              propertyId: p.propertyId ?? "",
              serviceTypeId: p.serviceTypeId ?? "",
              taskId: null,
              providerId: p.providerId ?? "",
              date: p.date ?? new Date().toISOString(),
              durationMinutes: p.durationMinutes ?? 0,
              amountBilled: p.amountBilled ?? 0,
              status: "done",
              notes: `Créé automatiquement depuis : "${text.slice(0, 80)}"`,
            },
          ];
        }

        if (action.type === "create_incident") {
          const p = action.payload as Partial<{
            propertyId: string;
            type: string;
            severity: string;
            description: string;
          }>;
          incidents = [
            ...incidents,
            {
              id: `inc_ai_${Date.now()}`,
              propertyId: p.propertyId ?? "",
              taskId: null,
              type: (p.type ?? "degats_voyageur") as Incident["type"],
              severity: (p.severity ?? "medium") as Incident["severity"],
              description: p.description ?? "",
              status: "open" as const,
              createdAt: new Date().toISOString(),
            },
          ];
        }
      });

      return { tasks, incidents, interventions, messages };
    });

    return result;
  },
}));
