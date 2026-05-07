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
    <main className="min-h-screen flex items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="font-serif text-3xl font-semibold tracking-tight">
            Lexitor
          </Link>
          <p className="mt-2 text-sm text-slate-600">Kreiraj radni prostor</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="bg-white border border-slate-200 rounded-lg p-8 space-y-5"
        >
          <div>
            <label htmlFor="full_name" className="block text-sm font-medium text-slate-700">
              Ime i prezime
            </label>
            <input
              id="full_name"
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="project_name" className="block text-sm font-medium text-slate-700">
              Naziv tvrtke / radnog prostora
            </label>
            <input
              id="project_name"
              type="text"
              required
              minLength={2}
              maxLength={255}
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700">
              Lozinka <span className="text-slate-400 text-xs">(min. 8 znakova)</span>
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border-slate-300 shadow-sm focus:border-brand-500 focus:ring-brand-500 px-3 py-2 border"
            />
          </div>

          {error && (
            <p className="text-sm text-status-fail bg-red-50 border border-red-100 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-brand-900 px-4 py-2.5 text-white font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            {submitting ? "Registriram…" : "Registriraj se"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-600">
          Već imate račun?{" "}
          <Link href="/login" className="text-brand-700 hover:underline font-medium">
            Prijavi se
          </Link>
        </p>
      </div>
    </main>
  );
}
