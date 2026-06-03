"use client";

import { useState } from "react";
import { AiKeyDialog } from "./AiKeyDialog";
import { ClassifiedStamp } from "./ClassifiedStamp";
import { CompileSequence } from "./CompileSequence";
import { DossierDisplay } from "./DossierDisplay";

type FormState = "idle" | "running" | "done" | "error";

export function DossierForm() {
  const [rootUrl, setRootUrl] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [company, setCompany] = useState("");
  const [state, setState] = useState<FormState>("idle");
  const [dossier, setDossier] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [aiQuestions, setAiQuestions] = useState<string[]>([]);

  async function runAi(provider: "anthropic" | "openai", key: string, model: string) {
    if (!dossier) return;
    const system =
      "You are helping a cybersecurity candidate prep for an interview. The user " +
      "will provide structured OSINT findings. Generate 3-7 NEW interview questions " +
      "as a numbered list. Return ONLY the list.";
    const prompt =
      "## Findings\n\n```json\n" +
      JSON.stringify(dossier, null, 2) +
      "\n```\n\n## Task\n\nGenerate 3-7 NEW questions as a numbered list.";
    const res = await fetch("/api/ai", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, key, model, system, prompt }),
    });
    const data = await res.json();
    if (data.text) {
      const lines = (data.text as string)
        .split("\n")
        .map((l) => l.match(/^\s*\d+[.):]\s*(.+)/))
        .filter((m): m is RegExpMatchArray => !!m)
        .map((m) => m[1].trim());
      setAiQuestions(lines);
    }
  }

  // When NEXT_PUBLIC_DEMO_MODE is set at build time, the site is a static
  // export (e.g. GitHub Pages) with no Python backend. The form still renders
  // so the design is on display, but submission shows a clear notice instead
  // of failing silently.
  const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (demoMode) {
      setError(
        "This page is the design preview — no Python backend is running here. " +
          "To actually run a dossier you have two options. " +
          "(1) Local CLI: pipx install git+https://github.com/scottalt/tradecraft-osint.git, then run tradecraft <url>. " +
          "(2) One-click hosted: deploy the same web app + Python functions to Vercel using the Deploy Button at " +
          "https://github.com/scottalt/tradecraft-osint/blob/main/web/DEPLOY.md — about 60 seconds.",
      );
      setState("error");
      return;
    }
    setState("running");
    setError(null);
    try {
      const res = await fetch("/api/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          root_url: rootUrl.trim(),
          job_url: jobUrl.trim() || null,
          company: company.trim() || null,
        }),
      });
      if (!res.ok) {
        // Surface the API's actual reason (e.g. unresolvable URL, rate limit)
        // instead of a bare status code.
        let message = `Server returned ${res.status}`;
        try {
          const err = await res.json();
          if (err?.error) message = err.error;
          if (err?.retry_after) {
            message += ` Try again in ~${Math.ceil(err.retry_after / 60)} min.`;
          }
        } catch {
          // non-JSON error body; keep the status-code message
        }
        throw new Error(message);
      }
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
            className="compile-cta font-typewriter uppercase tracking-widest text-lg px-8 py-3 bg-ink text-paper hover:bg-stamp-red transition-colors disabled:bg-faded-ink"
          >
            {state === "running" ? "Compiling …" : "Compile Dossier"}
          </button>
          {state === "running" && <ClassifiedStamp label="IN PROGRESS" rotation={2} variant="blue" />}
        </div>
      </form>
      {state === "running" && <CompileSequence />}
      {error && (
        <p className="mt-6 font-typewriter text-stamp-red text-sm">ERROR: {error}</p>
      )}
      {state === "done" && dossier !== null && (
        <>
          <DossierDisplay dossier={dossier as never} />
          <div className="mt-8 flex gap-4 items-center border-t-2 border-rule pt-6">
            <button
              type="button"
              onClick={() => setAiOpen(true)}
              className="font-typewriter uppercase tracking-widest text-sm px-6 py-2 border-2 border-ink text-ink"
            >
              Deep dive with AI (BYOK)
            </button>
            <span className="font-prose text-xs text-faded-ink italic">
              Your key never leaves this request.
            </span>
          </div>
          {aiQuestions.length > 0 && (
            <section className="mt-10">
              <p className="font-typewriter text-xs tracking-widest text-stamp-red mb-3">
                DEEP DIVE — AI
              </p>
              <ol className="space-y-4 font-prose list-decimal pl-6">
                {aiQuestions.map((q, i) => (
                  <li key={i} className="text-ink">
                    {q}
                  </li>
                ))}
              </ol>
            </section>
          )}
          <AiKeyDialog open={aiOpen} onClose={() => setAiOpen(false)} onSubmit={runAi} />
        </>
      )}
    </section>
  );
}
