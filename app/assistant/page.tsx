"use client";

import { Send, Sparkles } from "lucide-react";
import { useState } from "react";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { answerQuestion, SUGGESTED_QUESTIONS } from "@/lib/assistant";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

export default function AssistantPage() {
  const { properties, providers, tasks, incidents, reservations } = useStore();
  const [input, setInput] = useState("");
  const [chat, setChat] = useState<ChatMsg[]>([
    {
      role: "assistant",
      content:
        "Bonjour 👋 Je suis votre assistant opérationnel. Posez-moi une question sur vos logements, prestataires ou missions.",
    },
  ]);

  function ask(question: string) {
    if (!question.trim()) return;
    const reply = answerQuestion(question, {
      properties,
      providers,
      tasks,
      incidents,
      reservations,
    });
    setChat((c) => [
      ...c,
      { role: "user", content: question },
      { role: "assistant", content: reply },
    ]);
    setInput("");
  }

  return (
    <>
      <Topbar title="Assistant IA" />
      <div className="flex flex-col gap-4 p-5">
        <div className="flex flex-wrap gap-2">
          {SUGGESTED_QUESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              className="rounded-full border bg-card px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              {s}
            </button>
          ))}
        </div>

        <Card className="flex-1">
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
            ask(input);
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
    </>
  );
}
