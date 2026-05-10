"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/contexts/auth-context";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prijava neuspješna.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-surface text-ink px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <Link href="/" className="font-display text-3xl font-semibold tracking-tight text-ink">
            Lexitor
          </Link>
          <p className="mt-2 text-sm text-muted">Prijava u radni prostor</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="bg-surface-2 border border-brand-border rounded-lg p-8 space-y-5"
        >
          <Field label="Email" htmlFor="email">
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label="Lozinka" htmlFor="password">
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
          </Field>

          {error && (
            <p className="text-sm bg-status-fail/10 border border-status-fail/30 text-status-fail rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-ink px-4 py-2.5 text-surface font-medium hover:bg-navy transition disabled:opacity-50"
          >
            {submitting ? "Prijavljujem…" : "Prijavi se"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          Nemate račun?{" "}
          <Link href="/register" className="text-signal hover:underline font-medium">
            Registriraj se
          </Link>
        </p>
      </div>
    </main>
  );
}

const inputClass =
  "mt-1 block w-full rounded-md border border-brand-border bg-surface-2 shadow-sm focus:border-signal focus:ring-2 focus:ring-signal/20 px-3 py-2 outline-none transition";

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="block text-sm font-medium text-navy">
        {label}
      </label>
      {children}
    </div>
  );
}
