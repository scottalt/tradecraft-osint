import { DossierForm } from "./components/DossierForm";
import { IntelHero } from "./components/hero/IntelHero";

export default function HomePage() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-10">
      <IntelHero />

      <section className="mb-10 font-prose text-ink leading-relaxed max-w-3xl">
        <p>
          Submit a target organization below. The service will run a small set of public
          reconnaissance routines and return a field dossier — DNS posture, subdomain
          exposure, GitHub footprint, job description, and a starter set of interview
          questions evidence-cited to the findings.
        </p>
        <p className="mt-4">
          For the full collector roster (news, breaches, M&amp;A, people, business), use{" "}
          <a
            href="https://github.com/scottalt/tradecraft-osint"
            className="underline decoration-stamp-red underline-offset-4"
          >
            the local CLI
          </a>
          . This hosted preview is deliberately narrow.
        </p>
      </section>

      <DossierForm />

      <footer className="mt-16 pt-8 border-t border-rule text-faded-ink text-sm font-prose">
        <p>
          Hosted preview is a public demo. Targets are not stored. AI analysis is
          bring-your-own-key, proxied per request, never logged. See{" "}
          <a href="https://github.com/scottalt/tradecraft-osint/blob/main/docs/ETHICS.md" className="underline">
            ETHICS.md
          </a>
          .
        </p>
      </footer>
    </main>
  );
}
