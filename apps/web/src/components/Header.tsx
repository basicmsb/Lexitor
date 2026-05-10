"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { ThemeToggle } from "@/components/ThemeToggle";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3001";

const nav = [
  { href: "/moduli/analiza-troskovnika", label: "Troškovnik" },
  { href: "/moduli/analiza-don", label: "DON" },
  { href: "/moduli/zalbe", label: "Žalbe" },
  { href: "/cjenik", label: "Cjenik" },
  { href: "/blog", label: "Blog" },
  { href: "/o-nama", label: "O nama" },
] as const;

export function Header() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-brand-border bg-surface/90 backdrop-blur">
      <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between gap-6">
        <Link
          href="/"
          className="font-display text-2xl font-semibold tracking-tight text-ink shrink-0"
        >
          Lexitor
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm text-navy">
          {nav.map((item) => {
            const active = pathname === item.href || pathname?.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`transition hover:text-ink ${
                  active ? "text-ink font-medium" : ""
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3 shrink-0">
          <ThemeToggle />
          <a
            href={APP_URL}
            className="hidden md:inline-block rounded-md bg-ink px-4 py-2 text-sm font-medium text-surface hover:bg-navy transition"
          >
            Prijavi se
          </a>
          <button
            type="button"
            onClick={() => setMobileOpen((v) => !v)}
            className="md:hidden p-2 rounded-md hover:bg-surface-2 transition"
            aria-label="Otvori navigaciju"
          >
            <span className="block w-5 h-0.5 bg-ink mb-1" />
            <span className="block w-5 h-0.5 bg-ink mb-1" />
            <span className="block w-5 h-0.5 bg-ink" />
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="md:hidden border-t border-brand-border bg-surface">
          <nav className="px-6 py-4 flex flex-col gap-1 text-sm">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className="py-2 text-navy hover:text-ink transition"
              >
                {item.label}
              </Link>
            ))}
            <a
              href={APP_URL}
              className="mt-2 rounded-md bg-ink px-4 py-2.5 text-center text-sm font-medium text-surface hover:bg-navy transition"
            >
              Prijavi se
            </a>
          </nav>
        </div>
      )}
    </header>
  );
}
