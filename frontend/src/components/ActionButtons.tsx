"use client";

import { ChatAction } from "@/lib/api";

interface ActionButtonsProps {
  actions: ChatAction[];
  onAction: (action: string, payload?: Record<string, unknown>) => void;
  disabled?: boolean;
}

export default function ActionButtons({ actions, onAction, disabled }: ActionButtonsProps) {
  if (!actions.length) return null;

  return (
    <div className="flex flex-wrap gap-2 animate-fade-in">
      {actions.map((a) => (
        <button
          key={a.action}
          onClick={() => onAction(a.action, a.payload)}
          disabled={disabled}
          className="rounded-full border border-purple/40 bg-purple/10 px-4 py-2 text-sm font-medium text-purple-light transition-all hover:bg-purple/20 hover:border-purple/60 disabled:opacity-50"
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}
