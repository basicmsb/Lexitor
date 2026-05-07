import type { Metadata } from "next";
import {
  Fraunces,
  Inter,
  Instrument_Serif,
  JetBrains_Mono,
  Source_Serif_4,
} from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/auth-context";

const sans = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-sans",
  display: "swap",
});

const serif = Source_Serif_4({
  subsets: ["latin", "latin-ext"],
  variable: "--font-serif",
  display: "swap",
});

const display = Fraunces({
  subsets: ["latin", "latin-ext"],
  variable: "--font-display",
  display: "swap",
});

const accent = Instrument_Serif({
  subsets: ["latin", "latin-ext"],
  variable: "--font-accent",
  display: "swap",
  weight: "400",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Lexitor App",
    template: "%s | Lexitor",
  },
  description: "Lexitor radna ploča — analiza dokumentacije javne nabave.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="hr"
      className={`${sans.variable} ${serif.variable} ${display.variable} ${accent.variable} ${mono.variable}`}
    >
      <body className="font-sans antialiased bg-surface text-ink">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
