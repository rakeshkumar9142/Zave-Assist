"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  DashboardStats,
  Ticket,
  formatNumber,
  getDashboardStats,
  getTickets,
} from "@/lib/api";

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5 transition-colors hover:border-purple/30">
      <p className="text-xs font-medium uppercase tracking-wider text-muted">{label}</p>
      <p className={`mt-2 text-2xl font-bold ${accent || "text-foreground"}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-muted">{sub}</p>}
    </div>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-500/10 text-red-400",
    high: "bg-orange-500/10 text-orange-400",
    medium: "bg-yellow-500/10 text-yellow-400",
    low: "bg-green-500/10 text-green-400",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase ${colors[priority] || colors.medium}`}>
      {priority}
    </span>
  );
}

export default function AdminPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getDashboardStats(), getTickets()])
      .then(([s, t]) => {
        setStats(s);
        setTickets(t);
      })
      .catch(() => setError("Unable to connect to backend. Start the API server on port 8000."));
  }, []);

  const internalPct = stats
    ? ((stats.resolved_internal / stats.total_queries) * 100).toFixed(1)
    : "0";

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-xl font-bold">Admin Dashboard</h1>
            <p className="text-sm text-muted">Zave Assist Analytics</p>
          </div>
          <Link
            href="/"
            className="rounded-full border border-border px-4 py-2 text-sm text-muted transition-colors hover:border-purple/40 hover:text-foreground"
          >
            ← Back to Chat
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 py-8">
        {error && (
          <div className="mb-6 rounded-2xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning">
            {error}
          </div>
        )}

        {stats && (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
              <StatCard
                label="Total Queries"
                value={formatNumber(stats.total_queries)}
                sub="Monthly volume"
              />
              <StatCard
                label="Resolved (Internal)"
                value={formatNumber(stats.resolved_internal)}
                sub={`${internalPct}% — no AI needed`}
                accent="text-success"
              />
              <StatCard
                label="Resolved (Gemini)"
                value={formatNumber(stats.resolved_gemini)}
                sub="Product recommendations"
                accent="text-purple-light"
              />
              <StatCard
                label="Escalated to Humans"
                value={formatNumber(stats.escalated)}
                sub="Complex cases"
                accent="text-warning"
              />
              <StatCard
                label="Open Tickets"
                value={stats.open_tickets.toString()}
                sub="Awaiting resolution"
              />
              <StatCard
                label="Avg Resolution Time"
                value={`${stats.avg_resolution_time_seconds}s`}
                sub="End-to-end"
              />
              <StatCard
                label="Blocked Irrelevant"
                value={formatNumber(stats.blocked_irrelevant)}
                sub="Tokens saved"
              />
              <StatCard
                label="Token Savings"
                value={formatNumber(stats.estimated_token_savings)}
                sub="Estimated monthly"
                accent="text-purple-light"
              />
            </div>

            <div className="mt-6 rounded-2xl border border-border bg-surface p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-muted">
                    Customer Satisfaction
                  </p>
                  <p className="mt-1 text-4xl font-bold text-purple-light">
                    {stats.customer_satisfaction_score}
                    <span className="text-lg text-muted">/5.0</span>
                  </p>
                </div>
                <div className="text-right text-sm text-muted">
                  <p>Decision Engine</p>
                  <p className="text-foreground">87% resolved without AI</p>
                </div>
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-border">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-purple-dark to-purple-light"
                  style={{ width: `${(stats.customer_satisfaction_score / 5) * 100}%` }}
                />
              </div>
            </div>

            {/* Resolution breakdown bar */}
            <div className="mt-6 rounded-2xl border border-border bg-surface p-6">
              <p className="mb-4 text-xs font-medium uppercase tracking-wider text-muted">
                Resolution Breakdown
              </p>
              <div className="flex h-4 overflow-hidden rounded-full">
                <div
                  className="bg-success"
                  style={{ width: `${(stats.resolved_internal / stats.total_queries) * 100}%` }}
                  title="Internal"
                />
                <div
                  className="bg-purple"
                  style={{ width: `${(stats.resolved_gemini / stats.total_queries) * 100}%` }}
                  title="Gemini"
                />
                <div
                  className="bg-warning"
                  style={{ width: `${(stats.escalated / stats.total_queries) * 100}%` }}
                  title="Escalated"
                />
                <div
                  className="bg-border"
                  style={{ width: `${(stats.blocked_irrelevant / stats.total_queries) * 100}%` }}
                  title="Blocked"
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-success" /> Internal Systems
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-purple" /> Gemini Flash
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-warning" /> Escalated
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-border" /> Blocked
                </span>
              </div>
            </div>
          </>
        )}

        {/* Tickets */}
        <div className="mt-8">
          <h2 className="mb-4 text-lg font-semibold">Open Escalation Tickets</h2>
          {tickets.length === 0 ? (
            <p className="text-sm text-muted">No open tickets from this session.</p>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface text-left text-xs uppercase tracking-wider text-muted">
                    <th className="px-4 py-3">Ticket ID</th>
                    <th className="px-4 py-3">Reason</th>
                    <th className="px-4 py-3">Priority</th>
                    <th className="px-4 py-3">User</th>
                    <th className="px-4 py-3">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((t) => (
                    <tr key={t.id} className="border-b border-border/50 hover:bg-surface-hover">
                      <td className="px-4 py-3 font-mono text-purple-light">{t.id}</td>
                      <td className="px-4 py-3">{t.reason}</td>
                      <td className="px-4 py-3">
                        <PriorityBadge priority={t.priority} />
                      </td>
                      <td className="px-4 py-3 text-muted">{t.email || t.user_id}</td>
                      <td className="px-4 py-3 text-muted">
                        {new Date(t.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
