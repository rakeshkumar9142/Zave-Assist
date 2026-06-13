const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatAction {
  label: string;
  action: string;
  payload?: Record<string, unknown>;
}

export interface ChatResponse {
  message: string;
  intent: string;
  resolution_type: string;
  actions: ChatAction[];
  session_id: string;
  awaiting_input?: string;
  ticket_id?: string;
}

export interface DashboardStats {
  total_queries: number;
  resolved_internal: number;
  resolved_gemini: number;
  escalated: number;
  open_tickets: number;
  avg_resolution_time_seconds: number;
  blocked_irrelevant: number;
  estimated_token_savings: number;
  customer_satisfaction_score: number;
}

export interface Ticket {
  id: string;
  user_id: string;
  email?: string;
  order_id?: string;
  reason: string;
  priority: string;
  status: string;
  created_at: string;
}

export async function sendMessage(
  message: string,
  sessionId: string,
  userEmail?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      user_email: userEmail,
    }),
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
}

export async function sendAction(
  sessionId: string,
  action: string,
  payload?: Record<string, unknown>
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, action, payload }),
  });
  if (!res.ok) throw new Error("Failed to send action");
  return res.json();
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_URL}/api/admin/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function getTickets(): Promise<Ticket[]> {
  const res = await fetch(`${API_URL}/api/admin/tickets`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch tickets");
  return res.json();
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

export function formatMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br />");
}
