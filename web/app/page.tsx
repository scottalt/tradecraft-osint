import { DossierForm } from "./components/DossierForm";
import { IntelHero } from "./components/hero/IntelHero";

export default function HomePage() {
  return (
    <main className="max-w-4xl mx-auto px-6 py-10">
      <IntelHero />

      <section
        className="rise mb-10 font-prose text-ink leading-relaxed max-w-3xl"
        style={{ animationDelay: "220ms" }}
      >
        <p>
          Submit a target organization below. The service runs public-source
          reconnaissance and returns a field dossier — the company&apos;s industry and
          what it actually does, recent news and M&amp;A, GitHub footprint, the job&apos;s
          tech stack — then a set of <em>interview questions worth asking</em>, each cited
          to the evidence that prompted it.
        </p>
        <p className="mt-4">
          For breaches, deeper people analysis, and optional bring-your-own-key AI, use{" "}
          <a
            href="https://github.com/scottalt/tradecraft-osint"
            className="underline decoration-stamp-red underline-offset-4"
          >
            the local CLI
          </a>
          . Targets are not stored.
        </p>
      </section>

      <div className="rise" style={{ animationDelay: "340ms" }}>
        <DossierForm />
      </div>

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
