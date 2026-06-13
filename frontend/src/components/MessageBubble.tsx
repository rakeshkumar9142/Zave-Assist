"use client";

import { formatMarkdown } from "@/lib/api";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  resolutionType?: string;
}

export default function MessageBubble({ role, content, resolutionType }: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex animate-fade-in ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed sm:max-w-[75%] ${
          isUser
            ? "rounded-br-md bg-purple text-white"
            : "rounded-bl-md bg-surface border border-border"
        }`}
      >
        {!isUser && resolutionType && (
          <span className="mb-1.5 inline-block rounded-full bg-purple/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-purple-light">
            {resolutionType === "internal" && "Instant"}
            {resolutionType === "gemini" && "AI Recommendation"}
            {resolutionType === "escalated" && "Escalated"}
            {resolutionType === "blocked" && "Blocked"}
          </span>
        )}
        <div
          className="prose prose-invert prose-sm max-w-none"
          dangerouslySetInnerHTML={{ __html: formatMarkdown(content) }}
        />
      </div>
    </div>
  );
}
