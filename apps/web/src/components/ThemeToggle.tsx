"use client";

import { useTheme, type Theme } from "@/hooks/useTheme";

const options: { value: Theme; label: string; icon: string }[] = [
  { value: "light", label: "Svijetlo", icon: "☀" },
  { value: "dark", label: "Tamno", icon: "☾" },
  { value: "system", label: "Sustav", icon: "◐" },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="inline-flex gap-1 p-1 rounded-md bg-surface-2 border border-brand-border">
      {options.map((opt) => {
        const active = theme === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => setTheme(opt.value)}
            title={opt.label}
            aria-label={`Tema: ${opt.label}`}
            className={`w-7 h-7 text-xs rounded transition ${
              active ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink"
            }`}
          >
            <span aria-hidden="true">{opt.icon}</span>
          </button>
        );
      })}
    </div>
  );
}
