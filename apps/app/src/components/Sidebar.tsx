"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/contexts/auth-context";

const navigation = [
  { href: "/dashboard", label: "Naslovna" },
  { href: "/analiza/troskovnik", label: "Analiza troškovnika" },
  { href: "/analiza/don", label: "Analiza DON-a" },
  { href: "/zalbe", label: "Žalbe" },
  { href: "/pretraga", label: "Pretraga prakse" },
  { href: "/dokumentacija", label: "Dokumentacija" },
  { href: "/clanci", label: "Članci" },
  { href: "/upute", label: "Upute" },
  { href: "/paketi", label: "Paketi" },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { me, logout } = useAuth();

  return (
    <aside className="w-64 shrink-0 border-r border-brand-border bg-surface min-h-screen flex flex-col">
      <div className="px-6 py-5 border-b border-brand-border">
        <Link href="/dashboard" className="font-display text-2xl font-semibold tracking-tight text-ink">
          Lexitor
        </Link>
        {me?.project && (
          <p className="text-xs text-muted mt-1 truncate">{me.project.name}</p>
        )}
      </div>

      <nav className="p-3 flex-1">
        <ul className="space-y-1">
          {navigation.map((item) => {
            const active = pathname?.startsWith(item.href);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`block px-3 py-2 rounded-md text-sm transition ${
                    active
                      ? "bg-surface-2 text-ink font-medium"
                      : "text-navy hover:bg-surface-2 hover:text-ink"
                  }`}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="p-3 border-t border-brand-border">
        {me?.user && (
          <div className="px-3 py-2 mb-2">
            <p className="text-sm font-medium text-ink truncate">
              {me.user.full_name ?? me.user.email}
            </p>
            <p className="text-xs text-muted truncate">{me.user.email}</p>
          </div>
        )}
        <button
          type="button"
          onClick={logout}
          className="block w-full text-left px-3 py-2 rounded-md text-sm text-navy hover:bg-surface-2"
        >
          Odjavi se
        </button>
      </div>
    </aside>
  );
}
