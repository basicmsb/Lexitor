import Link from "next/link";

const navigation = [
  { href: "/dashboard", label: "Naslovna" },
  { href: "/analiza/troskovnik", label: "Analiza troškovnika" },
  { href: "/analiza/don", label: "Analiza DON-a" },
  { href: "/zalbe", label: "Žalbe" },
  { href: "/clanci", label: "Članci" },
  { href: "/upute", label: "Upute" },
  { href: "/paketi", label: "Paketi" },
] as const;

export function Sidebar() {
  return (
    <aside className="w-64 shrink-0 border-r border-slate-200 bg-white min-h-screen">
      <div className="px-6 py-5 border-b border-slate-200">
        <Link href="/dashboard" className="font-serif text-2xl font-semibold tracking-tight">
          Lexitor
        </Link>
      </div>
      <nav className="p-3">
        <ul className="space-y-1">
          {navigation.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="block px-3 py-2 rounded-md text-sm text-slate-700 hover:bg-slate-100"
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
