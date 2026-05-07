export default function DashboardPage() {
  return (
    <div>
      <h1 className="font-serif text-3xl font-semibold mb-2">Dobro došli u Lexitor</h1>
      <p className="text-slate-600">
        Ovdje će biti pregled nedavnih analiza i brzih akcija.
      </p>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <a
          href="/analiza/troskovnik"
          className="block rounded-lg border border-slate-200 bg-white p-6 hover:border-brand-500"
        >
          <h3 className="font-semibold text-slate-900">Analiza troškovnika</h3>
          <p className="mt-2 text-sm text-slate-600">
            Učitaj troškovnik i provjeri stavke protiv ZJN-a.
          </p>
        </a>
        <a
          href="/analiza/don"
          className="block rounded-lg border border-slate-200 bg-white p-6 hover:border-brand-500"
        >
          <h3 className="font-semibold text-slate-900">Analiza DON-a</h3>
          <p className="mt-2 text-sm text-slate-600">
            Provjeri dokumentaciju o nabavi prije objave.
          </p>
        </a>
        <a
          href="/zalbe"
          className="block rounded-lg border border-slate-200 bg-white p-6 hover:border-brand-500"
        >
          <h3 className="font-semibold text-slate-900">Žalbe</h3>
          <p className="mt-2 text-sm text-slate-600">
            Generiraj nacrt žalbe ili odgovora <em>(Faza 2)</em>.
          </p>
        </a>
      </div>
    </div>
  );
}
