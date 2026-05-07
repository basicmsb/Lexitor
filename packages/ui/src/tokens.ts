/**
 * Lexitor brand tokens — single source of truth for colors, fonts, and
 * status semantics. Both apps/web and apps/app reference these values
 * (via tailwind.config.ts re-export, see lexitorTheme below).
 *
 * Source: C:\Dropbox\_Lexitor\Grafika\Web design\2026\Stil web-a\
 *   - Color tokens.html
 *   - Status indikatori.html
 *   - Type specimen.html
 *
 * Tagline: "Mirno, precizno, suvremeno"
 * Slogan:  "Usklađenost bez stresa."
 */

export const colors = {
  // Brand palette ------------------------------------------------------------
  surface: "#FAFAF8", // toplo bijela pozadina
  surface2: "#F2F2EE", // Mist — sekcije, kartice
  ink: "#0B1320", // primarni text / dark mode bg
  navy: "#1A2332", // sekundarni / heading
  muted: "#6B7587", // tihi tekst, meta
  signal: "#3B82C4", // primarni accent (plavi)
  gold: "#B8893E", // sekundarni accent (zlatni)
  border: "#E0E0DA", // subtilni border (rgb 224, 224, 218)
  white: "#FFFFFF",

  // Status colors (prigušene, profesionalne) ---------------------------------
  status: {
    ok: "#3F7D45", // Usklađeno
    warn: "#A87F2E", // Upozorenje
    fail: "#A8392B", // Kršenje
    uncertain: "#6B4A8E", // Pravna nesigurnost
    accepted: "#2A6DB0", // Prihvaćen rizik
    neutral: "#7B7363", // Nije provjereno
  },
} as const;

export const fonts = {
  display: "Fraunces", // Hero / display tipografija
  heading: '"Source Serif 4"', // H1-H4
  body: "Inter", // Body, UI tekst
  citation: '"JetBrains Mono"', // Pravni citati, klasa brojevi
  accent: '"Instrument Serif"', // Specijalni naglasci
} as const;

export const messages = {
  tagline: "Mirno, precizno, suvremeno",
  slogan: "Usklađenost bez stresa.",
} as const;

/**
 * Tailwind theme.extend block consumed by apps/web and apps/app.
 * Imported as: `import { lexitorTheme } from "@lexitor/ui/theme"`.
 */
export const lexitorTheme: {
  colors: Record<string, string | Record<string, string>>;
  fontFamily: Record<string, string[]>;
} = {
  colors: {
    brand: {
      ink: colors.ink,
      navy: colors.navy,
      signal: colors.signal,
      gold: colors.gold,
      surface: colors.surface,
      surface2: colors.surface2,
      muted: colors.muted,
      border: colors.border,
    },
    surface: colors.surface,
    "surface-2": colors.surface2,
    ink: colors.ink,
    navy: colors.navy,
    signal: colors.signal,
    gold: colors.gold,
    muted: colors.muted,
    status: { ...colors.status },
  },
  fontFamily: {
    sans: ["var(--font-sans)", fonts.body, "system-ui", "sans-serif"],
    serif: ["var(--font-serif)", fonts.heading, "Georgia", "serif"],
    display: ["var(--font-display)", fonts.display, "Georgia", "serif"],
    accent: ["var(--font-accent)", fonts.accent, "Georgia", "serif"],
    mono: ["var(--font-mono)", fonts.citation, "ui-monospace", "monospace"],
  },
};
