"use client";

import { Bot, CheckCircle2, Send, Sparkles, Zap } from "lucide-react";
import { useState } from "react";
import { Topbar } from "@/components/layout/topbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { answerQuestion, SUGGESTED_QUESTIONS } from "@/lib/assistant";
import { EXAMPLE_MESSAGES } from "@/lib/ai-processor";
import type { ProcessedMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";

type Tab = "chatbot" | "operator";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

const CONFIDENCE_BADGE = {
  high: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  medium: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  low: "bg-red-500/15 text-red-600 dark:text-red-400",
};

const CONFIDENCE_LABEL = { high: "Confiance haute", medium: "Confiance moyenne", low: "Confiance faible" };

const ACTION_ICON: Record<string, string> = {
  update_task: "✅",
  create_intervention: "📋",
  log_hours: "⏱️",
  create_incident: "⚠️",
};

export default function AssistantPage() {
  const store = useStore();
  const [tab, setTab] = useState<Tab>("operator");
  const [input, setInput] = useState("");
  const [chat, setChat] = useState<ChatMsg[]>([
    {
      role: "assistant",
      content:
        "Bonjour 👋 Je suis votre assistant opérationnel. Posez-moi une question sur vos logements, prestataires ou missions.",
    },
  ]);
  const [opInput, setOpInput] = useState("");
  const [opResults, setOpResults] = useState<ProcessedMessage[]>([]);
  const [processing, setProcessing] = useState(false);

  function askChatbot(question: string) {
    if (!question.trim()) return;
    const reply = answerQuestion(question, store);
    setChat((c) => [
      ...c,
      { role: "user", content: question },
      { role: "assistant", content: reply },
    ]);
    setInput("");
  }

  function processOperatorMessage(text: string) {
    if (!text.trim()) return;
    setProcessing(true);
    // Simuler un léger délai (parsing + "IA")
    setTimeout(() => {
      const result = store.applyAIMessage(text);
      setOpResults((r) => [result, ...r]);
      setOpInput("");
      setProcessing(false);
    }, 600);
  }

  return (
    <>
      <Topbar title="IA & Assistant" />
      <div className="p-5">
        {/* Onglets ─────────────────────────────────── */}
        <div className="mb-5 flex gap-1 rounded-lg border bg-muted/40 p-1 w-fit">
          <button
            onClick={() => setTab("operator")}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
              tab === "operator"
                ? "bg-primary text-primary-foreground shadow"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Zap className="h-4 w-4" /> IA Opérateur (WhatsApp / Vocal)
          </button>
          <button
            onClick={() => setTab("chatbot")}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
              tab === "chatbot"
                ? "bg-primary text-primary-foreground shadow"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Sparkles className="h-4 w-4" /> Assistant IA
          </button>
        </div>

        {/* ═══ MODE IA OPÉRATEUR ══════════════════════ */}
        {tab === "operator" && (
          <div className="space-y-5">
            {/* Explication */}
            <Card className="border-primary/30 bg-primary/5">
              <CardContent className="flex gap-3 p-4 text-sm">
                <Bot className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                <div>
                  <p className="font-semibold text-primary">IA Opérationnelle — sans saisie manuelle</p>
                  <p className="mt-1 text-muted-foreground">
                    Collez ou dictez un message WhatsApp ou une note vocale. L'IA extrait les
                    informations opérationnelles, met à jour les missions, enregistre les heures,
                    crée les interventions et déclenche les incidents — automatiquement.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Messages exemples */}
            <div>
              <p className="mb-2 text-xs font-medium text-muted-foreground">
                Exemples de messages
              </p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_MESSAGES.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => setOpInput(ex)}
                    className="rounded-full border bg-card px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            {/* Zone de saisie */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                processOperatorMessage(opInput);
              }}
              className="flex gap-2"
            >
              <input
                value={opInput}
                onChange={(e) => setOpInput(e.target.value)}
                placeholder="Ex : &laquo; J'ai terminé le Chalet A12 à 13h45 &raquo;"
                className="h-10 flex-1 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <Button
                type="submit"
                disabled={processing || !opInput.trim()}
                size="icon"
                className="h-10 w-10"
              >
                {processing ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </form>

            {/* Résultats de traitement */}
            {opResults.length === 0 && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                Envoyez un message pour voir l'IA l'analyser et agir.
              </p>
            )}
            {opResults.map((res, idx) => (
              <Card key={idx} className="animate-fade-in">
                <CardHeader className="pb-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-mono text-sm">« {res.original} »</p>
                    <Badge className={CONFIDENCE_BADGE[res.confidence]}>
                      {CONFIDENCE_LABEL[res.confidence]}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-2 pt-1 text-xs text-muted-foreground">
                    {res.detectedProperty && <span>📍 {res.detectedProperty}</span>}
                    {res.detectedProvider && <span>👤 {res.detectedProvider}</span>}
                    {res.raw.durationMinutes && (
                      <span>⏱ {res.raw.durationMinutes} min</span>
                    )}
                    {res.raw.endTime && (
                      <span>
                        🕒 fin {new Date(res.raw.endTime).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    )}
                    {res.raw.detectedServices.length > 0 && (
                      <span>🧹 {res.raw.detectedServices.join(", ")}</span>
                    )}
                    {res.raw.detectedIncident && (
                      <span>⚠️ incident : {res.raw.detectedIncident}</span>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-2 pt-0">
                  {res.actions.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Aucune action déclenchée — informations insuffisantes.
                    </p>
                  ) : (
                    res.actions.map((action, ai) => (
                      <div
                        key={ai}
                        className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2 text-sm"
                      >
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                        <span className="mr-1">{ACTION_ICON[action.type]}</span>
                        <span>{action.description}</span>
                        <Badge className="ml-auto bg-muted text-muted-foreground text-xs">
                          {action.type}
                        </Badge>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* ═══ MODE CHATBOT ═══════════════════════════ */}
        {tab === "chatbot" && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => askChatbot(s)}
                  className="rounded-full border bg-card px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>

            <Card>
              <CardContent className="space-y-3 p-5">
                {chat.map((m, idx) => (
                  <div
                    key={idx}
                    className={cn(
                      "flex gap-3",
                      m.role === "user" ? "justify-end" : "justify-start",
                    )}
                  >
                    {m.role === "assistant" && (
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                        <Sparkles className="h-4 w-4" />
                      </div>
                    )}
                    <div
                      className={cn(
                        "max-w-[75%] whitespace-pre-line rounded-2xl px-4 py-2.5 text-sm",
                        m.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary",
                      )}
                    >
                      {m.content}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                askChatbot(input);
              }}
              className="flex gap-2"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Posez votre question…"
                className="h-10 flex-1 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <Button type="submit" size="icon" className="h-10 w-10">
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </div>
        )}
      </div>
    </>
  );
}
