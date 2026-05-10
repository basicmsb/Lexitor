import type { Config } from "tailwindcss";

import { lexitorTheme } from "../../packages/ui/theme";

/**
 * Dark mode strategija: class-based (`html.dark`). Theme toggle u
 * `useTheme` hook-u dodaje/uklanja `dark` klasu na `<html>`. Boje koje
 * trebaju biti theme-aware koriste CSS varijable definirane u globals.css
 * (`var(--color-surface)` itd.). Statične `brand.*` boje ostaju za
 * elemente koji su uvijek isti (npr. logo, brand accent).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Theme-aware (mijenjaju se s dark mode-om kroz CSS vars)
        surface: "var(--color-surface)",
        "surface-2": "var(--color-surface-2)",
        ink: "var(--color-ink)",
        navy: "var(--color-navy)",
        muted: "var(--color-muted)",
        signal: "var(--color-signal)",
        gold: "var(--color-gold)",
        status: {
          ok: "var(--color-status-ok)",
          warn: "var(--color-status-warn)",
          fail: "var(--color-status-fail)",
          uncertain: "var(--color-status-uncertain)",
          accepted: "var(--color-status-accepted)",
          neutral: "var(--color-status-neutral)",
        },
        "brand-border": "var(--color-border)",
        "overlay-soft": "var(--color-overlay-soft)",
        "overlay-medium": "var(--color-overlay-medium)",
        // Statične brand boje (ne mijenjaju se s mode-om)
        brand: lexitorTheme.colors.brand,
      },
      fontFamily: lexitorTheme.fontFamily,
    },
  },
  plugins: [],
};

export default config;
