"use client";

import { useEffect, useState } from "react";

export type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "lexitor-theme";

/**
 * Theme hook — class-based dark mode (Tailwind `darkMode: 'class'`).
 *
 * Toggle: `setTheme("light" | "dark" | "system")`.
 * - "system" prati OS preference kroz `prefers-color-scheme` media query
 * - Spremljeno u localStorage, sinkronizira preko više tab-ova
 * - Početni render — uvijek light (SSR safe), prebaci na pravu vrijednost u `useEffect`
 */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("light");
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");

  // Initial load — pročitaj iz localStorage
  useEffect(() => {
    const stored = (localStorage.getItem(STORAGE_KEY) as Theme | null) ?? "system";
    setThemeState(stored);
  }, []);

  // Resolve theme + apply class kad god se promijeni
  useEffect(() => {
    const root = document.documentElement;
    const apply = () => {
      let resolved: "light" | "dark";
      if (theme === "system") {
        resolved = window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
      } else {
        resolved = theme;
      }
      setResolvedTheme(resolved);
      if (resolved === "dark") {
        root.classList.add("dark");
      } else {
        root.classList.remove("dark");
      }
    };
    apply();

    // Sluša promjene OS preference samo ako je theme="system"
    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      mq.addEventListener("change", apply);
      return () => mq.removeEventListener("change", apply);
    }
  }, [theme]);

  const setTheme = (next: Theme) => {
    setThemeState(next);
    localStorage.setItem(STORAGE_KEY, next);
  };

  return { theme, resolvedTheme, setTheme };
}
