"use client";

import { useState } from "react";
import { ClassifiedStamp } from "./ClassifiedStamp";

type FormState = "idle" | "running" | "done" | "error";

export function DossierForm() {
  const [rootUrl, setRootUrl] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [company, setCompany] = useState("");
  const [state, setState] = useState<FormState>("idle");
  const [dossier, setDossier] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setState("running");
    setError(null);
    try {
      const res = await fetch("/api/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          root_url: rootUrl,
          job_url: jobUrl || null,
          company: company || null,
        }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setDossier(data);
      setState("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setState("error");
    }
  }

  return (
    <section className="border-2 border-ink p-8 bg-paper relative">
      <p className="font-typewriter text-xs tracking-widest absolute top-2 right-4 text-faded-ink">
        OPS / INTAKE
      </p>
      <form onSubmit={submit} className="space-y-6">
        <div>
          <label className="font-typewriter text-sm uppercase tracking-wider block mb-2 text-ink">
            FROM: target root URL
          </label>
          <input
            type="url"
            required
            placeholder="https://acme.com"
            value={rootUrl}
            onChange={(e) => setRootUrl(e.target.value)}
            className="w-full border-b-2 border-ink bg-transparent font-data text-lg py-2 focus:outline-none focus:border-stamp-red"
          />
        </div>
        <div>
          <label className="font-typewriter text-sm uppercase tracking-wider block mb-2 text-ink">
            SUBJECT: job listing URL (optional)
          </label>
          <input
            type="url"
            placeholder="https://acme.com/careers/sec-eng"
            value={jobUrl}
            onChange={(e) => setJobUrl(e.target.value)}
            className="w-full border-b-2 border-ink bg-transparent font-data text-lg py-2 focus:outline-none focus:border-stamp-red"
          />
        </div>
        <div>
          <label className="font-typewriter text-sm uppercase tracking-wider block mb-2 text-ink">
            ALIAS: company name (auto-inferred if blank)
          </label>
          <input
            type="text"
            placeholder="Acme Corp"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            className="w-full border-b-2 border-ink bg-transparent font-data text-lg py-2 focus:outline-none focus:border-stamp-red"
          />
        </div>
        <div className="flex items-center gap-6 pt-4">
          <button
            type="submit"
            disabled={state === "running"}
            className="font-typewriter uppercase tracking-widest text-lg px-8 py-3 bg-ink text-paper hover:bg-stamp-red transition-colors disabled:bg-faded-ink"
          >
            {state === "running" ? "Compiling …" : "Compile Dossier"}
          </button>
          {state === "running" && <ClassifiedStamp label="IN PROGRESS" rotation={2} variant="blue" />}
        </div>
      </form>
      {error && (
        <p className="mt-6 font-typewriter text-stamp-red text-sm">ERROR: {error}</p>
      )}
      {state === "done" && dossier !== null && (
        <pre className="mt-10 border-t-2 border-rule pt-6 text-xs font-data overflow-auto max-h-[60vh] text-ink">
          {JSON.stringify(dossier, null, 2)}
        </pre>
      )}
    </section>
  );
}
