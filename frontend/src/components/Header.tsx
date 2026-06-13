"use client";

import Link from "next/link";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple/20 pulse-glow">
            <span className="text-lg font-bold text-purple-light">Z</span>
          </div>
          <div>
            <h1 className="text-base font-semibold leading-tight">Zave Assist</h1>
            <p className="text-xs text-muted">AI Shopping Support</p>
          </div>
        </Link>
        <nav className="flex items-center gap-2">
          <Link
            href="/admin"
            className="rounded-full px-3 py-1.5 text-xs text-muted transition-colors hover:bg-surface hover:text-foreground"
          >
            Admin
          </Link>
          <div className="flex items-center gap-1.5 rounded-full bg-success/10 px-2.5 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
            <span className="text-xs text-success">Online</span>
          </div>
        </nav>
      </div>
    </header>
  );
}
