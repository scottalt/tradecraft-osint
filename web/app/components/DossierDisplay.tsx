import { SectionHeader } from "./SectionHeader";
import { DataTable } from "./DataTable";
import { RedactionReveal } from "./RedactionReveal";

type Dossier = {
  target: { company_name: string; root_url: string; job_url?: string | null };
  results: Array<{
    name: string;
    data: Record<string, unknown>;
    signals: string[];
    errors: Array<{ stage: string; message: string }>;
    duration_ms: number;
  }>;
  questions: Array<{
    text: string;
    confidence: string;
    source_collector: string;
    is_starred: boolean;
    evidence?: {
      summary: string;
      url?: string | null;
      date?: string | null;
      source: string;
    } | null;
  }>;
};

export function DossierDisplay({ dossier }: { dossier: Dossier }) {
  const collector = (name: string) => dossier.results.find((r) => r.name === name);

  const footprint = collector("footprint");
  const company = collector("company");
  const job = collector("job");
  const github = collector("github");

  return (
    <article className="mt-12">
      <p className="font-typewriter text-xs tracking-widest text-faded-ink mb-2">
        FILE NO. {Math.floor(Math.random() * 9000 + 1000)} ·{" "}
        {new Date().toISOString().slice(0, 10)}
      </p>
      <h2 className="font-typewriter text-3xl text-ink mb-2">
        {dossier.target.company_name}
      </h2>
      <p className="font-data text-faded-ink mb-8">{dossier.target.root_url}</p>

      {footprint && (
        <>
          <SectionHeader index="01" label="WEB & INFRASTRUCTURE FOOTPRINT" />
          <DataTable
            rows={[
              { label: "Host", value: (footprint.data.host as string) ?? "—" },
              { label: "Server", value: (footprint.data.server as string) ?? "—" },
              { label: "X-Powered-By", value: (footprint.data.x_powered_by as string) ?? "—" },
              {
                label: "Security headers",
                value:
                  Object.keys((footprint.data.security_headers as object) ?? {}).join(", ") ||
                  "(none)",
              },
              {
                label: "Subdomains observed",
                value: ((footprint.data.subdomains as string[]) ?? []).length,
              },
              {
                label: "Signals",
                value: footprint.signals.join(", ") || "(none)",
              },
            ]}
          />
        </>
      )}

      {company && (company.data.pages as unknown[])?.length ? (
        <>
          <SectionHeader index="02" label="COMPANY PROFILE" />
          <ul className="space-y-3 font-prose">
            {((company.data.pages as Array<{ path: string; title?: string }>) ?? []).map(
              (p, i) => (
                <li key={i}>
                  <span className="font-typewriter text-sm uppercase text-faded-ink">
                    /{p.path}
                  </span>{" "}
                  — {p.title ?? "(untitled)"}
                </li>
              ),
            )}
          </ul>
        </>
      ) : null}

      {job && (job.data.title as string) ? (
        <>
          <SectionHeader index="03" label="ROLE-FIT SIGNALS (FROM JD)" />
          <DataTable
            rows={[
              { label: "Title", value: (job.data.title as string) ?? "—" },
              { label: "Host", value: (job.data.host as string) ?? "—" },
              {
                label: "Stack mentioned",
                value: ((job.data.stack as string[]) ?? []).join(", ") || "(none)",
              },
            ]}
          />
        </>
      ) : null}

      {github && (github.data.org as object | null) ? (
        <>
          <SectionHeader index="04" label="GITHUB PRESENCE" />
          <DataTable
            rows={[
              { label: "Org", value: ((github.data.org as { login?: string })?.login) ?? "—" },
              { label: "Repos visible", value: (github.data.repo_count as number) ?? 0 },
              {
                label: "Languages",
                value: Object.entries(
                  (github.data.languages as Record<string, number>) ?? {},
                )
                  .slice(0, 6)
                  .map(([k, v]) => `${k} (${v})`)
                  .join(", "),
              },
              { label: "Signals", value: github.signals.join(", ") || "(none)" },
            ]}
          />
        </>
      ) : null}

      <SectionHeader index="05" label="QUESTIONS TO ASK" />
      {dossier.questions.length === 0 ? (
        <p className="font-prose italic text-faded-ink">
          No heuristic questions fired. Try adding a job listing URL or run the CLI for the
          full collector roster.
        </p>
      ) : (
        <ol className="space-y-4 font-prose list-decimal pl-6">
          {dossier.questions.map((q, i) => (
            <li key={i} className="text-ink">
              <RedactionReveal index={i}>
                <span className={q.is_starred ? "font-semibold" : ""}>{q.text}</span>
                <span className="block font-typewriter text-xs uppercase text-faded-ink mt-1 tracking-wider">
                  · {q.confidence} · {q.source_collector}
                </span>
              {q.evidence ? (
                <span className="block font-typewriter text-xs text-faded-ink mt-1 tracking-wider">
                  source:{" "}
                  {(() => {
                    const safeUrl =
                      q.evidence?.url && /^https?:\/\//i.test(q.evidence.url)
                        ? q.evidence.url
                        : null;
                    return safeUrl ? (
                      <a
                        href={safeUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline text-stamp-blue underline-offset-2"
                      >
                        {q.evidence!.source}
                        {q.evidence!.date ? ` · ${q.evidence!.date}` : ""}
                      </a>
                    ) : (
                      <span>
                        {q.evidence!.source}
                        {q.evidence!.date ? ` · ${q.evidence!.date}` : ""}
                      </span>
                    );
                  })()}
                </span>
                ) : null}
              </RedactionReveal>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}
