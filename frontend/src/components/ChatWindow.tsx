"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ActionButtons from "./ActionButtons";
import MessageBubble from "./MessageBubble";
import { ChatAction, sendAction, sendMessage } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  resolutionType?: string;
  actions?: ChatAction[];
}

const QUICK_PROMPTS = [
  "Where is my order?",
  "My cashback hasn't been credited",
  "My coupon isn't working",
  "Suggest earbuds under ₹2,000",
];

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = sessionStorage.getItem("zave_session_id");
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem("zave_session_id", id);
  }
  return id;
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi! I'm Zave Assist — your shopping support specialist. How can I help you today?",
      resolutionType: "internal",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setSessionId(getSessionId());
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const addAssistantMessage = useCallback(
    (content: string, resolutionType?: string, actions?: ChatAction[]) => {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content,
          resolutionType,
          actions,
        },
      ]);
    },
    []
  );

  const handleSend = async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || loading || !sessionId) return;

    setInput("");
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: msg }]);
    setLoading(true);

    try {
      const response = await sendMessage(msg, sessionId);
      addAssistantMessage(response.message, response.resolution_type, response.actions);
    } catch {
      addAssistantMessage(
        "I'm having trouble connecting right now. Please try again in a moment.",
        "internal"
      );
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleAction = async (action: string, payload?: Record<string, unknown>) => {
    if (loading || !sessionId) return;
    setLoading(true);
    try {
      const response = await sendAction(sessionId, action, payload);
      addAssistantMessage(response.message, response.resolution_type, response.actions);
    } catch {
      addAssistantMessage("Action failed. Please try again.", "internal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto flex max-w-2xl flex-col gap-4">
          {messages.map((m) => (
            <div key={m.id}>
              <MessageBubble
                role={m.role}
                content={m.content}
                resolutionType={m.resolutionType}
              />
              {m.actions && m.actions.length > 0 && (
                <div className="mt-2 ml-1">
                  <ActionButtons
                    actions={m.actions}
                    onAction={handleAction}
                    disabled={loading}
                  />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex justify-start animate-fade-in">
              <div className="flex items-center gap-1 rounded-2xl rounded-bl-md bg-surface border border-border px-4 py-3">
                <span className="typing-dot h-2 w-2 rounded-full bg-purple-light" />
                <span className="typing-dot h-2 w-2 rounded-full bg-purple-light" />
                <span className="typing-dot h-2 w-2 rounded-full bg-purple-light" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Quick prompts */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2">
          <div className="mx-auto flex max-w-2xl flex-wrap gap-2">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => handleSend(prompt)}
                className="rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-muted transition-colors hover:border-purple/40 hover:text-foreground"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-border bg-background/80 backdrop-blur-xl px-4 py-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="mx-auto flex max-w-2xl items-center gap-2"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about orders, cashback, coupons..."
            disabled={loading}
            className="flex-1 rounded-full border border-border bg-surface px-4 py-3 text-sm outline-none transition-colors placeholder:text-muted focus:border-purple/50 focus:ring-1 focus:ring-purple/30 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-purple text-white transition-all hover:bg-purple-dark disabled:opacity-40"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
              <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
