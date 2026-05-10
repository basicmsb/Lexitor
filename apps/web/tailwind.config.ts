import type { Config } from "tailwindcss";

import { lexitorTheme } from "../../packages/ui/theme";

const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Theme-aware (light/dark mode kroz CSS vars)
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
        },
        "brand-border": "var(--color-border)",
        // Statične brand boje (ne mijenjaju se)
        brand: lexitorTheme.colors.brand,
      },
      fontFamily: lexitorTheme.fontFamily,
    },
  },
  plugins: [],
};

export default config;
