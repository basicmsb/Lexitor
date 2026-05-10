"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/contexts/auth-context";

export default function RegisterPage() {
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [projectName, setProjectName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await register({
        email,
        password,
        full_name: fullName || undefined,
        project_name: projectName,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registracija neuspješna.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-surface text-ink px-4 py-10">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <Link href="/" className="font-display text-3xl font-semibold tracking-tight text-ink">
            Lexitor
          </Link>
          <p className="mt-2 text-sm text-muted">Kreiraj radni prostor</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="bg-surface-2 border border-brand-border rounded-lg p-8 space-y-5"
        >
          <Field label="Ime i prezime" htmlFor="full_name">
            <input
              id="full_name"
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className={inputClass}
            />
          </Field>

          <Field label="Naziv tvrtke / radnog prostora" htmlFor="project_name">
            <input
              id="project_name"
              type="text"
              required
              minLength={2}
              maxLength={255}
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className={inputClass}
            />
          </Field>

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

          <Field label="Lozinka" hint="min. 8 znakova" htmlFor="password">
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              maxLength={128}
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
            {submitting ? "Registriram…" : "Registriraj se"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          Već imate račun?{" "}
          <Link href="/login" className="text-signal hover:underline font-medium">
            Prijavi se
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
  hint,
  htmlFor,
  children,
}: {
  label: string;
  hint?: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="block text-sm font-medium text-navy">
        {label}
        {hint && <span className="ml-2 text-xs text-muted">({hint})</span>}
      </label>
      {children}
    </div>
  );
}
