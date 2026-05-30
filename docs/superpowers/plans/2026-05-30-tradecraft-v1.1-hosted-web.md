# tradecraft v1.1 — Hosted Web Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a hosted demo of tradecraft at a public URL (`tradecraft-osint.vercel.app` or user's custom domain). Single-page web app: user pastes a company URL + optional job listing, server runs the four `safe_for_hosted=True` collectors via a Vercel Python Function calling the existing tradecraft core, server returns a Findings JSON, browser renders the dossier in a deliberately-distinctive "Field Dossier" visual style. Optional BYOK AI proxied per-request, key never stored.

**Architecture:** A `web/` subdirectory at the repo root, deployed as a single Vercel project. Next.js 16 App Router with Turbopack for the frontend. One Vercel Python Function (`api/compile.py`) that vendors `src/tradecraft/` at build time and exposes `POST /api/compile`. One additional Python Function (`api/ai.py`) for BYOK AI proxying — accepts provider + key + prompt, forwards to provider, returns response, never logs or persists the key. Per-IP rate limiting via Routing Middleware backed by Vercel Runtime Cache. Vercel BotID enabled.

**Tech Stack:** Next.js 16 + React 19 + TypeScript + Tailwind v4 + Turbopack. Vercel Python Functions (Fluid Compute, Python 3.13). Vercel Routing Middleware (Node.js runtime) for rate limit. Vercel BotID. The existing `tradecraft` package (vendored at build time).

**Spec reference:** `docs/superpowers/specs/2026-05-23-tradecraft-design.md` §10 (Hosted preview). Memory: `feedback_hosted_services.md` — BYOK only, never store keys, narrow legal exposure.

**Visual direction — "Field Dossier":**
The aesthetic is intentionally NOT a standard AI/shadcn-default web app. Instead, it leans into the brand name (`tradecraft` = intelligence-community term) and produces something that feels like a classified field briefing.

- **Color palette:**
  - `--paper`: `#f4ead6` (warm manila paper, page background)
  - `--ink`: `#1a1612` (deep typewriter black, body text)
  - `--stamp-red`: `#b8231a` (classification stamp + active signals)
  - `--stamp-blue`: `#1a3a5c` (headers + secondary stamps)
  - `--faded-ink`: `#5a5046` (metadata, footnotes)
  - `--rule`: `#c4b8a0` (hairline borders, dividers)
- **Typography (Google Fonts):**
  - Display/headers: **"Special Elite"** — typewriter font with worn-key character. Used for the title, section markers, and any stamp labels.
  - Body & data: **"JetBrains Mono"** — monospace for OSINT data tables (IPs, hashes, domains). Reads "professional analyst," not "casual chatbot."
  - Long prose: **"IBM Plex Serif"** — for prose paragraphs in the briefing intro.
- **Texture:** subtle SVG paper-grain background (~5% opacity noise) on `--paper`. No glass/blur/gradients.
- **Information density:** tables with hairline rules, numbered lists, footnotes, "FROM:/TO:/SUBJECT:" header blocks. The opposite of a marketing landing page.
- **Decorative elements:** lightly-rotated "CLASSIFIED" / "EYES ONLY" / "FIELD REPORT" stamps in `--stamp-red`. Used sparingly as section headers and the page hero.
- **NO:** light/dark toggle (it's always day-mode cream), gradient backgrounds, shadcn `Card`/`Button` defaults, generic Tailwind palette colors, Inter font, hero gradients.

When the frontend-design skill is invoked at execution time, this section is the brief.

**Out of scope (deferred):**
- User accounts, persistent dossier history.
- Asynchronous job queue (v1.1 is synchronous; if the timeout is hit, the dossier streams partial results).
- Custom domain. v1.1 ships on `*.vercel.app`.
- The five `safe_for_hosted=False` collectors (`news`, `breaches`, `people`, `business`, `ma`). The hosted product is deliberately narrow — see ETHICS.md.

---

## File map

Files to **create** in `web/`:

```
web/
├── .gitignore
├── package.json
├── tsconfig.json
├── next.config.ts
├── vercel.ts                          # Vercel project config
├── postcss.config.mjs                 # Tailwind v4
├── app/
│   ├── globals.css                    # Tailwind layers + Field Dossier tokens
│   ├── layout.tsx                     # <html> shell + font loading
│   ├── page.tsx                       # Home / form page
│   ├── dossier/
│   │   └── [slug]/
│   │       └── page.tsx               # (optional, future) shareable URL
│   └── components/
│       ├── DossierForm.tsx            # The input form
│       ├── ClassifiedStamp.tsx        # Rotating stamp decoration
│       ├── SectionHeader.tsx          # Typewriter section heading
│       ├── DataTable.tsx              # Hairline-rule table for OSINT data
│       ├── FootprintCard.tsx          # Footprint section renderer
│       ├── CompanyCard.tsx            # Company section renderer
│       ├── JobCard.tsx                # Job section renderer
│       ├── GitHubCard.tsx             # GitHub section renderer
│       ├── QuestionsList.tsx          # Renders heuristic + AI questions
│       └── AiKeyDialog.tsx            # BYOK AI modal
├── api/
│   ├── compile.py                     # Vercel Python Function (tradecraft runner)
│   ├── ai.py                          # BYOK AI proxy Function
│   └── requirements.txt               # Python deps for both functions
├── middleware.ts                      # Routing Middleware (per-IP rate limit)
├── scripts/
│   └── vendor-tradecraft.sh           # Build hook: copy src/tradecraft → api/_vendor/
└── README.md                          # Web-app-specific README
```

Files to **modify** at repo root:

```
.gitignore                             # Add web/node_modules/, web/.next/, etc.
README.md                              # Add "Hosted version" section + link
CHANGELOG.md                           # Add 0.4.0 (or 1.1.0) entry
src/tradecraft/__init__.py             # Version bump (1.1.0 or 0.4.0)
```

---

## Conventions used in every task

- **Package manager:** `pnpm` (faster, deterministic, default for new Vercel projects in 2026). If pnpm isn't installed, use `npm` instead.
- **Tests:** v1.1 ships a **smoke test** for the API endpoints (using `node --test` + `fetch`) and **Playwright** for the home page render. No unit tests for the React components (YAGNI for an alpha demo).
- **Run dev:** `pnpm dev` (from `web/`) starts Next.js + the Python Functions locally via `vercel dev`.
- **Commits:** Conventional Commits. One commit per task.
- **Co-author trailer:** include `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` on every commit.

## Browser support matrix

Modern evergreens (last 2 versions of Chrome/Edge/Firefox/Safari). No IE / no legacy fallbacks.

---

## Task 1: Scaffold the web subdirectory

**Files:**
- Create: `web/package.json`
- Create: `web/tsconfig.json`
- Create: `web/next.config.ts`
- Create: `web/.gitignore`
- Modify: `.gitignore` (repo root) — append `web/node_modules/`, `web/.next/`, `web/.vercel/`

- [ ] **Step 1: Create `web/package.json`**

```json
{
  "name": "tradecraft-web",
  "version": "1.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "next dev --turbopack",
    "build": "bash scripts/vendor-tradecraft.sh && next build --turbopack",
    "start": "next start",
    "lint": "next lint",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "^16.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/postcss": "^4.0.0",
    "postcss": "^8.4.0",
    "typescript": "^5.6.0"
  }
}
```

- [ ] **Step 2: Create `web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules", "api/_vendor"]
}
```

- [ ] **Step 3: Create `web/next.config.ts`**

```ts
import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  // Allow the Python Function path to coexist; Next.js ignores /api/*.py
  // because it isn't a JS/TS route.
};

export default config;
```

- [ ] **Step 4: Create `web/.gitignore`**

```
node_modules/
.next/
.vercel/
out/
*.tsbuildinfo
.env*.local
api/_vendor/
```

- [ ] **Step 5: Append to root `.gitignore`**

Add these lines at the end of `C:\Users\scott\Github\Interview-OSINT\.gitignore`:

```
# Web app
web/node_modules/
web/.next/
web/.vercel/
web/api/_vendor/
```

- [ ] **Step 6: Install web deps**

From the repo root:

```
cd web
pnpm install
# or if pnpm is missing: npm install
```

This populates `web/node_modules/` and creates `web/pnpm-lock.yaml`.

- [ ] **Step 7: Verify scaffold compiles**

```
cd web
pnpm typecheck
```

Expected: success (no source files yet, but TypeScript should accept the config). If it complains about no input, that's fine for now — Task 3 adds the first .tsx file.

- [ ] **Step 8: Commit**

From the repo root:

```
git add web/package.json web/tsconfig.json web/next.config.ts web/.gitignore web/pnpm-lock.yaml .gitignore
git commit -m "$(cat <<'EOF'
feat(web): scaffold Next.js 16 + Tailwind v4 subdirectory

pnpm-driven Next.js project under web/ with Turbopack for dev and
build. TypeScript strict mode. Excludes api/_vendor (populated at
build by scripts/vendor-tradecraft.sh).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Tailwind v4 + Field Dossier design tokens

**Files:**
- Create: `web/postcss.config.mjs`
- Create: `web/app/globals.css`

Tailwind v4 uses CSS-first config: design tokens live in `@theme { ... }` blocks inside the stylesheet instead of `tailwind.config.js`. We define the Field Dossier color palette + custom fonts here.

- [ ] **Step 1: Create `web/postcss.config.mjs`**

```js
export default {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
```

- [ ] **Step 2: Create `web/app/globals.css`**

```css
@import "tailwindcss";

/* Field Dossier design tokens — referenced by Tailwind v4 utilities as
   bg-paper, text-ink, text-stamp-red, etc. */
@theme {
  --color-paper: #f4ead6;
  --color-ink: #1a1612;
  --color-stamp-red: #b8231a;
  --color-stamp-blue: #1a3a5c;
  --color-faded-ink: #5a5046;
  --color-rule: #c4b8a0;

  --font-typewriter: "Special Elite", "Courier New", monospace;
  --font-data: "JetBrains Mono", "SF Mono", monospace;
  --font-prose: "IBM Plex Serif", Georgia, serif;
}

/* Page-level baseline: cream paper with subtle grain texture. */
html {
  background: var(--color-paper);
  color: var(--color-ink);
  font-family: var(--font-prose);
}

body {
  /* SVG paper-grain texture. Inline so we don't ship a separate asset. */
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/%3E%3CfeColorMatrix values='0 0 0 0 0.5 0 0 0 0 0.45 0 0 0 0 0.4 0 0 0 0.05 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  min-height: 100vh;
}

/* Typewriter heading default. Apply explicitly via font-typewriter Tailwind class. */
h1, h2, h3 {
  font-family: var(--font-typewriter);
  letter-spacing: 0.02em;
}

/* Monospace data style. */
.data-cell {
  font-family: var(--font-data);
  font-size: 0.9em;
}

/* Hairline rule used in tables and section dividers. */
.rule {
  border: 1px solid var(--color-rule);
}

/* Stamp-style decorations get a deliberate skew + uppercase letterforms. */
.stamp {
  font-family: var(--font-typewriter);
  text-transform: uppercase;
  color: var(--color-stamp-red);
  border: 2px solid var(--color-stamp-red);
  padding: 0.25em 0.75em;
  display: inline-block;
  letter-spacing: 0.15em;
  transform: rotate(-2deg);
}
```

- [ ] **Step 3: Verify the styles compile**

```
cd web
pnpm build
```

If `pnpm build` complains because `app/layout.tsx` doesn't exist yet, that's expected. Task 3 creates it.

- [ ] **Step 4: Commit**

```
git add web/postcss.config.mjs web/app/globals.css
git commit -m "$(cat <<'EOF'
feat(web): Tailwind v4 + Field Dossier design tokens

CSS-first Tailwind theme. Field Dossier palette (manila paper, ink
black, classification red, stamp blue, faded ink, hairline rule).
Three fonts: Special Elite for headings, JetBrains Mono for data,
IBM Plex Serif for prose. Inline SVG paper-grain texture, no
external asset. Stamp utility class for rotated CLASSIFIED-style
decorations.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Layout + font loading + landing page

**Files:**
- Create: `web/app/layout.tsx`
- Create: `web/app/page.tsx`
- Create: `web/app/components/ClassifiedStamp.tsx`
- Create: `web/app/components/SectionHeader.tsx`

This is where the frontend-design skill's aesthetic decisions land in code. The implementer should INVOKE the frontend-design skill with this section's design brief if they want to elaborate the visual treatment further; otherwise the code below is sufficient for an alpha.

- [ ] **Step 1: Create `web/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "tradecraft — field dossier",
  description:
    "OSINT dossier for cybersecurity interview prep. Recon your future employer.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Special+Elite&family=JetBrains+Mono:wght@400;600&family=IBM+Plex+Serif:wght@400;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 2: Create `web/app/components/ClassifiedStamp.tsx`**

```tsx
type StampProps = {
  label: string;
  rotation?: number;
  variant?: "red" | "blue";
};

export function ClassifiedStamp({ label, rotation = -3, variant = "red" }: StampProps) {
  const color = variant === "red" ? "var(--color-stamp-red)" : "var(--color-stamp-blue)";
  return (
    <span
      className="stamp"
      style={{
        transform: `rotate(${rotation}deg)`,
        color,
        borderColor: color,
      }}
    >
      {label}
    </span>
  );
}
```

- [ ] **Step 3: Create `web/app/components/SectionHeader.tsx`**

```tsx
import type { ReactNode } from "react";

type Props = {
  index: string; // e.g. "01"
  label: string; // e.g. "WEB & INFRASTRUCTURE"
  children?: ReactNode;
};

export function SectionHeader({ index, label, children }: Props) {
  return (
    <header className="mt-12 mb-6 border-t-2 border-b-2 border-rule py-3 flex items-baseline gap-6">
      <span className="font-typewriter text-sm tracking-widest text-faded-ink">§ {index}</span>
      <h2 className="font-typewriter text-2xl uppercase tracking-wide text-ink">{label}</h2>
      {children}
    </header>
  );
}
```

- [ ] **Step 4: Create `web/app/page.tsx` (home / form page)**

```tsx
import { ClassifiedStamp } from "./components/ClassifiedStamp";
import { DossierForm } from "./components/DossierForm";

export default function HomePage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-12">
      <header className="border-b-2 border-ink pb-8 mb-10 flex items-start justify-between">
        <div>
          <p className="font-typewriter text-xs tracking-widest text-faded-ink mb-2">
            FILE NO. 0001-A · CLASSIFICATION: PUBLIC
          </p>
          <h1 className="font-typewriter text-5xl text-ink mb-2">tradecraft</h1>
          <p className="font-prose italic text-faded-ink">
            Recon your future employer before the interview.
          </p>
        </div>
        <ClassifiedStamp label="FIELD REPORT" rotation={-4} variant="red" />
      </header>

      <section className="mb-10 font-prose text-ink leading-relaxed">
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
```

- [ ] **Step 5: Verify build**

```
cd web
pnpm typecheck
```

Expected: fails because `DossierForm` doesn't exist yet. Task 4 creates it.

- [ ] **Step 6: Commit** (with the DossierForm stub from the next task to avoid a broken intermediate)

This task and Task 4 are committed together at the end of Task 4 so the build is green.

---

## Task 4: DossierForm component

**Files:**
- Create: `web/app/components/DossierForm.tsx`

- [ ] **Step 1: Create `web/app/components/DossierForm.tsx`**

```tsx
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
```

The raw JSON dump is a placeholder; Task 7 replaces it with proper section components (FootprintCard, CompanyCard, etc.).

- [ ] **Step 2: Verify build**

```
cd web
pnpm build
```

Expected: builds successfully (page + DossierForm). May fail on the `/api/compile` route at build time since the Python function doesn't exist yet — that's OK; Next.js doesn't validate Python files. If it actually breaks, add `/api/compile` to `next.config.ts`'s `serverExternalPackages` or just ignore — the function is server-side at deploy time.

- [ ] **Step 3: Commit (combine Task 3 and Task 4 here)**

```
git add web/app/layout.tsx web/app/page.tsx web/app/components/
git commit -m "$(cat <<'EOF'
feat(web): home page + Field Dossier form

Cream paper background, typewriter headers, classification stamp,
FROM/SUBJECT/ALIAS form fields styled as a field intake. POSTs to
/api/compile and dumps the raw JSON for now (Task 7 replaces with
proper section components). All visual decisions land here:
Special Elite display, JetBrains Mono data, IBM Plex Serif prose.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Vendor script + Python function entry + requirements

**Files:**
- Create: `web/scripts/vendor-tradecraft.sh`
- Create: `web/api/requirements.txt`
- Create: `web/api/_vendor/.gitkeep` (placeholder so the dir exists)

The vendor script copies `src/tradecraft/` into `web/api/_vendor/tradecraft/` at build time. The function imports it via `sys.path` manipulation since Python paths are relative to the function file.

- [ ] **Step 1: Create `web/scripts/vendor-tradecraft.sh`**

```bash
#!/usr/bin/env bash
# Copy the tradecraft Python package into web/api/_vendor/ so the
# Vercel Python Function can import it without going through PyPI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$WEB_DIR")"
SRC="$ROOT_DIR/src/tradecraft"
DEST="$WEB_DIR/api/_vendor/tradecraft"

if [ ! -d "$SRC" ]; then
  echo "ERROR: $SRC does not exist. Did you run this from the wrong place?"
  exit 1
fi

rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
cp -R "$SRC" "$DEST"

echo "Vendored tradecraft -> $DEST"
```

Make it executable:

```
chmod +x web/scripts/vendor-tradecraft.sh
```

- [ ] **Step 2: Create `web/api/requirements.txt`**

These are the Python deps for the Vercel Function. They mirror the runtime dependencies from `pyproject.toml`. We DON'T install `tradecraft` itself via pip — it's vendored.

```
httpx[http2]>=0.27
dnspython>=2.6
selectolax>=0.3.21
pydantic>=2.7
feedparser>=6.0
```

(`anthropic` and `openai` are NOT in this list — the AI proxy uses raw httpx so we don't bloat the function bundle.)

- [ ] **Step 3: Create the placeholder so `_vendor/` exists**

```
mkdir -p web/api/_vendor
touch web/api/_vendor/.gitkeep
```

Add `.gitkeep` to git but ensure the rest of `_vendor/` stays ignored:

Edit `web/.gitignore` to change `api/_vendor/` to `api/_vendor/*` and add `!api/_vendor/.gitkeep`:

```
node_modules/
.next/
.vercel/
out/
*.tsbuildinfo
.env*.local
api/_vendor/*
!api/_vendor/.gitkeep
```

- [ ] **Step 4: Run the vendor script locally to verify it works**

```
cd web
bash scripts/vendor-tradecraft.sh
ls api/_vendor/tradecraft/
```

Expected: see all the tradecraft module files (`__init__.py`, `collectors/`, etc.).

After verifying, clear `_vendor/` so we don't accidentally commit:

```
rm -rf api/_vendor/*
touch api/_vendor/.gitkeep
```

- [ ] **Step 5: Commit**

```
git add web/scripts/vendor-tradecraft.sh web/api/requirements.txt web/api/_vendor/.gitkeep web/.gitignore
git commit -m "$(cat <<'EOF'
feat(web): vendor script + Python function requirements

scripts/vendor-tradecraft.sh copies src/tradecraft/ into
web/api/_vendor/ at build time. The Vercel Function imports it
via sys.path; we don't ship to PyPI for v1.1. requirements.txt
pins the runtime Python deps (no anthropic / openai — the AI
proxy uses raw httpx).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Vercel Python function — `/api/compile`

**Files:**
- Create: `web/api/compile.py`

Runs the four `safe_for_hosted=True` collectors (`footprint`, `company`, `job`, `github`), assembles the dossier, returns JSON.

- [ ] **Step 1: Create `web/api/compile.py`**

```python
"""POST /api/compile — run hosted-safe collectors and return Findings JSON."""

from __future__ import annotations

import asyncio
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

# Add the vendored tradecraft package to sys.path. The build step
# (scripts/vendor-tradecraft.sh) copies it into ./_vendor/tradecraft/.
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE / "_vendor"))

# Now import tradecraft (must come AFTER sys.path mutation).
from tradecraft.analyzers.heuristics import generate_questions  # noqa: E402
from tradecraft.cache import Cache  # noqa: E402
from tradecraft.collectors.company import CompanyCollector  # noqa: E402
from tradecraft.collectors.footprint import FootprintCollector  # noqa: E402
from tradecraft.collectors.github import GitHubCollector  # noqa: E402
from tradecraft.collectors.job import JobCollector  # noqa: E402
from tradecraft.config import HttpConfig  # noqa: E402
from tradecraft.http import HttpClient  # noqa: E402
from tradecraft.models import Role, Target  # noqa: E402
from tradecraft.orchestrator import Orchestrator  # noqa: E402
from tradecraft.renderers.json import render_json  # noqa: E402


HOSTED_COLLECTORS = [
    FootprintCollector(),
    CompanyCollector(),
    JobCollector(),
    GitHubCollector(),
]


async def _run(payload: dict) -> str:
    root_url = payload["root_url"]
    job_url = payload.get("job_url") or None
    company_in = payload.get("company") or None

    company_name = company_in
    if not company_name:
        host = urlparse(root_url).hostname or root_url
        parts = host.split(".")
        company_name = parts[-2].capitalize() if len(parts) >= 2 else host

    target = Target(
        company_name=company_name,
        root_url=root_url,
        job_url=job_url,
        role=Role.CYBERSECURITY,
    )

    # Use an in-memory ephemeral cache per request — no persistence in hosted mode.
    cache = Cache(directory=Path("/tmp/tradecraft-cache"), default_ttl=60, enabled=False)
    target_host = urlparse(root_url).hostname

    async with HttpClient(HttpConfig(), cache, target_host=target_host) as http:
        orch = Orchestrator(HOSTED_COLLECTORS, http=http, cache=cache)
        findings = await orch.run(target, hosted=True)

    questions = generate_questions(findings)
    return render_json(findings, questions)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 — Vercel Python signature
        try:
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(body.decode("utf-8"))
            if not payload.get("root_url"):
                self._respond(400, {"error": "root_url required"})
                return
            result = asyncio.run(_run(payload))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self._respond(500, {"error": str(exc)[:200]})

    def _respond(self, status: int, body: dict) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002 — Vercel quiet
        return
```

- [ ] **Step 2: Local smoke test**

Install Vercel CLI if not present (the session-start hook already recommended this):

```
npm i -g vercel
```

From `web/`:

```
bash scripts/vendor-tradecraft.sh
vercel dev
```

In another shell:

```
curl -X POST http://localhost:3000/api/compile \
  -H "Content-Type: application/json" \
  -d '{"root_url":"https://example.com","company":"Example"}'
```

Expected: a JSON dossier with `schema_version: 1`, `target.company_name: "Example"`, and one or more collector results in `results`.

If `vercel dev` is not available, defer the smoke test to the deploy step (Task 11).

- [ ] **Step 3: Commit**

```
git add web/api/compile.py
git commit -m "$(cat <<'EOF'
feat(web): /api/compile Vercel Python Function

Runs the four hosted-safe collectors (footprint, company, job,
github) against the user's target. Imports tradecraft from
./_vendor (vendored at build time by scripts/vendor-tradecraft.sh).
Returns Findings JSON via render_json. Synchronous; one
request = one full collector run. Cache disabled per request
so no cross-tenant state. orchestrator runs with hosted=True
so safe_for_hosted=False collectors are skipped (defensive).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Per-collector section components + dossier renderer

**Files:**
- Create: `web/app/components/DataTable.tsx`
- Create: `web/app/components/DossierDisplay.tsx`
- Modify: `web/app/components/DossierForm.tsx`

Replace the raw JSON dump in `DossierForm` with structured section components.

- [ ] **Step 1: Create `web/app/components/DataTable.tsx`**

```tsx
type Row = { label: string; value: React.ReactNode };

export function DataTable({ rows }: { rows: Row[] }) {
  return (
    <table className="w-full text-sm border-collapse">
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-b border-rule align-top">
            <th className="text-left font-typewriter uppercase text-xs tracking-wider text-faded-ink py-3 pr-6 w-1/3">
              {r.label}
            </th>
            <td className="data-cell py-3 text-ink break-all">{r.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 2: Create `web/app/components/DossierDisplay.tsx`**

```tsx
import { SectionHeader } from "./SectionHeader";
import { DataTable } from "./DataTable";

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
              <span className={q.is_starred ? "font-semibold" : ""}>{q.text}</span>
              <span className="block font-typewriter text-xs uppercase text-faded-ink mt-1 tracking-wider">
                · {q.confidence} · {q.source_collector}
              </span>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}
```

- [ ] **Step 3: Modify `web/app/components/DossierForm.tsx` to use DossierDisplay**

Replace the entire `{state === "done" && dossier !== null && ( <pre ...>{JSON.stringify(...)} </pre> )}` block with:

```tsx
{state === "done" && dossier !== null && (
  <DossierDisplay dossier={dossier as never} />
)}
```

Add the import at the top of the file:

```tsx
import { DossierDisplay } from "./DossierDisplay";
```

- [ ] **Step 4: Verify build**

```
cd web
pnpm build
```

Expected: clean build. Warnings on unused vars are OK.

- [ ] **Step 5: Commit**

```
git add web/app/components/DataTable.tsx web/app/components/DossierDisplay.tsx web/app/components/DossierForm.tsx
git commit -m "$(cat <<'EOF'
feat(web): DossierDisplay with per-collector sections

DataTable component with hairline rules and typewriter labels.
DossierDisplay renders footprint / company / job / github sections
+ questions list. Sections are conditional — empty collectors don't
render an awkward stub. Form's raw JSON dump replaced.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: BYOK AI proxy function + frontend modal

**Files:**
- Create: `web/api/ai.py`
- Create: `web/app/components/AiKeyDialog.tsx`
- Modify: `web/app/components/DossierForm.tsx` (add "Deep dive with AI" button after dossier renders)

`api/ai.py` accepts `{provider, key, system, prompt}`, calls the provider, returns the text response. **The key is never logged, never persisted, never written to disk.**

- [ ] **Step 1: Create `web/api/ai.py`**

```python
"""POST /api/ai — BYOK proxy. Key arrives, gets used for one call, gets dropped."""

from __future__ import annotations

import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler

import httpx


async def _call_anthropic(key: str, system: str, prompt: str, model: str) -> str:
    resp = await _post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        body={
            "model": model,
            "max_tokens": 1200,
            "system": system,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}
                    ],
                }
            ],
        },
    )
    blocks = resp.get("content", [])
    for b in blocks:
        if isinstance(b, dict) and isinstance(b.get("text"), str):
            return b["text"]
    return ""


async def _call_openai(key: str, system: str, prompt: str, model: str, base_url: str | None = None) -> str:
    url = (base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    resp = await _post(
        url,
        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
        body={
            "model": model,
            "max_tokens": 1200,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        },
    )
    choices = resp.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "") or ""


async def _post(url: str, headers: dict, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        return r.json()


async def _generate(payload: dict) -> dict:
    provider = payload.get("provider")
    key = payload.get("key", "")
    system = payload.get("system", "")
    prompt = payload.get("prompt", "")
    model = payload.get("model", "")

    if provider == "anthropic":
        text = await _call_anthropic(key, system, prompt, model or "claude-sonnet-4-6")
    elif provider == "openai":
        text = await _call_openai(key, system, prompt, model or "gpt-4o")
    elif provider == "openai-compat":
        base_url = payload.get("base_url")
        if not base_url:
            return {"error": "base_url required for openai-compat"}
        text = await _call_openai(key, system, prompt, model, base_url=base_url)
    else:
        return {"error": f"unsupported provider: {provider!r}"}

    return {"text": text}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        try:
            length = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(body.decode("utf-8"))
            # DELIBERATELY: do not log payload (it contains the key).
            result = asyncio.run(_generate(payload))
            status = 400 if "error" in result else 200
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)[:200]}).encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        # IMPORTANT: do not log the payload — it contains the user's key.
        return
```

- [ ] **Step 2: Create `web/app/components/AiKeyDialog.tsx`**

```tsx
"use client";

import { useState } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
  onSubmit: (provider: "anthropic" | "openai", key: string, model: string) => Promise<void>;
};

export function AiKeyDialog({ open, onClose, onSubmit }: Props) {
  const [provider, setProvider] = useState<"anthropic" | "openai">("anthropic");
  const [key, setKey] = useState("");
  const [model, setModel] = useState("");
  const [running, setRunning] = useState(false);

  if (!open) return null;

  const defaultModel = provider === "anthropic" ? "claude-sonnet-4-6" : "gpt-4o";

  async function handle(e: React.FormEvent) {
    e.preventDefault();
    setRunning(true);
    try {
      await onSubmit(provider, key, model || defaultModel);
      onClose();
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-ink/40 flex items-center justify-center z-50">
      <div className="bg-paper border-2 border-ink max-w-lg w-full p-8 relative">
        <p className="font-typewriter text-xs tracking-widest absolute top-2 right-4 text-faded-ink">
          BYOK · LOCAL ONLY
        </p>
        <h3 className="font-typewriter text-xl uppercase mb-4">Deep dive with AI</h3>
        <p className="font-prose text-sm text-faded-ink mb-6">
          Your key is forwarded once to the provider and never stored or logged on this
          server. No persistence.
        </p>
        <form onSubmit={handle} className="space-y-4">
          <div>
            <label className="font-typewriter text-xs uppercase tracking-wider block mb-1">
              Provider
            </label>
            <div className="flex gap-3">
              {(["anthropic", "openai"] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setProvider(p)}
                  className={`font-typewriter uppercase text-sm px-3 py-1 border-2 ${
                    provider === p
                      ? "bg-ink text-paper border-ink"
                      : "bg-paper text-ink border-rule"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="font-typewriter text-xs uppercase tracking-wider block mb-1">
              API key
            </label>
            <input
              type="password"
              required
              value={key}
              onChange={(e) => setKey(e.target.value)}
              className="w-full border-b-2 border-ink bg-transparent font-data py-2 focus:outline-none focus:border-stamp-red"
            />
          </div>
          <div>
            <label className="font-typewriter text-xs uppercase tracking-wider block mb-1">
              Model (optional)
            </label>
            <input
              type="text"
              placeholder={defaultModel}
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full border-b-2 border-ink bg-transparent font-data py-2 focus:outline-none focus:border-stamp-red"
            />
          </div>
          <div className="flex gap-4 pt-2">
            <button
              type="submit"
              disabled={running || !key}
              className="font-typewriter uppercase tracking-widest text-sm px-6 py-2 bg-ink text-paper disabled:bg-faded-ink"
            >
              {running ? "Running …" : "Run AI"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="font-typewriter uppercase tracking-widest text-sm px-6 py-2 border-2 border-rule"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Wire the AI flow into `DossierForm.tsx`**

Update `DossierForm.tsx` to add the dialog open state + the call to `/api/ai`. Find the existing imports and add `AiKeyDialog`. Inside the component, add state and a submit handler that posts to `/api/ai` and appends the result as a single question.

Replace the `DossierForm` body to add the AI button and dialog. Find the line `{state === "done" && dossier !== null && (` and BEFORE that block, add:

```tsx
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
```

(This state lives alongside the existing `dossier` / `state` / `error` state.)

In the JSX, after the existing dossier block, add the AI button and the dialog:

```tsx
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
```

- [ ] **Step 4: Verify build**

```
cd web
pnpm build
```

- [ ] **Step 5: Commit**

```
git add web/api/ai.py web/app/components/AiKeyDialog.tsx web/app/components/DossierForm.tsx
git commit -m "$(cat <<'EOF'
feat(web): BYOK AI proxy + Deep Dive dialog

api/ai.py forwards a single request to the provider using the
user-supplied key, then discards. No logging. Supports anthropic
(with cache_control: ephemeral on the user message) and openai
(also covers openai-compat with a base_url). Frontend modal asks
for provider + key + optional model, parses the numbered-list
response into a Deep Dive (AI) section.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Routing Middleware (per-IP rate limit) + BotID

**Files:**
- Create: `web/middleware.ts`
- Create: `web/vercel.ts`

The middleware runs before every request to `/api/*`, hashes the client IP, looks it up in a simple in-memory window (acceptable for v1.1; a Vercel Runtime Cache / Edge Config upgrade is post-v1.1), and rejects with `429` after 3 requests per IP per hour.

Note: the middleware uses a process-local Map. Vercel Functions are stateless across cold starts, so the rate limit is "per instance per hour" — a slow leak. For v1.1 demo traffic this is fine. To make it global, swap for `@upstash/ratelimit` + Upstash Redis (Marketplace integration) post-v1.1.

- [ ] **Step 1: Create `web/middleware.ts`**

```ts
import { NextRequest, NextResponse } from "next/server";

const HITS: Map<string, { count: number; resetAt: number }> = new Map();
const WINDOW_MS = 60 * 60 * 1000;
const LIMIT = 3;

function clientIp(req: NextRequest): string {
  const fwd = req.headers.get("x-forwarded-for");
  if (fwd) return fwd.split(",")[0].trim();
  return req.headers.get("x-real-ip") ?? "0.0.0.0";
}

export function middleware(req: NextRequest) {
  if (!req.nextUrl.pathname.startsWith("/api/compile")) {
    return NextResponse.next();
  }
  const ip = clientIp(req);
  const now = Date.now();
  const entry = HITS.get(ip);
  if (!entry || now >= entry.resetAt) {
    HITS.set(ip, { count: 1, resetAt: now + WINDOW_MS });
    return NextResponse.next();
  }
  if (entry.count >= LIMIT) {
    const retryAfter = Math.ceil((entry.resetAt - now) / 1000);
    return new NextResponse(
      JSON.stringify({ error: "rate limit exceeded", retry_after: retryAfter }),
      {
        status: 429,
        headers: {
          "Content-Type": "application/json",
          "Retry-After": String(retryAfter),
        },
      },
    );
  }
  entry.count += 1;
  return NextResponse.next();
}

export const config = {
  matcher: "/api/compile/:path*",
};
```

- [ ] **Step 2: Create `web/vercel.ts`**

```ts
import { type VercelConfig } from "@vercel/config/v1";

export const config: VercelConfig = {
  buildCommand: "bash scripts/vendor-tradecraft.sh && pnpm build",
  framework: "nextjs",
  functions: {
    "api/compile.py": {
      runtime: "python3.13",
      memory: 1024,
      maxDuration: 60,
    },
    "api/ai.py": {
      runtime: "python3.13",
      memory: 512,
      maxDuration: 120,
    },
  },
};
```

Install the `@vercel/config` package:

```
cd web
pnpm add @vercel/config
```

If `@vercel/config` isn't yet published or pnpm can't resolve it, fall back to `vercel.json` with the equivalent contents:

```json
{
  "buildCommand": "bash scripts/vendor-tradecraft.sh && pnpm build",
  "framework": "nextjs",
  "functions": {
    "api/compile.py": { "runtime": "python3.13", "memory": 1024, "maxDuration": 60 },
    "api/ai.py": { "runtime": "python3.13", "memory": 512, "maxDuration": 120 }
  }
}
```

Delete `web/vercel.ts` if using the json fallback.

- [ ] **Step 3: Commit**

```
git add web/middleware.ts web/vercel.ts web/package.json web/pnpm-lock.yaml
git commit -m "$(cat <<'EOF'
feat(web): rate-limit middleware + vercel.ts project config

Per-IP rate limit on /api/compile (3 requests / IP / hour). In-memory
window — fine for demo traffic; upgrade to Upstash Redis later if
needed. vercel.ts pins python3.13 runtime, memory, and maxDuration
for both functions. Build command vendors tradecraft first.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Web README + Linked from root README

**Files:**
- Create: `web/README.md`
- Modify: `README.md` (repo root) — append a "Hosted version" section

- [ ] **Step 1: Create `web/README.md`**

```markdown
# tradecraft-web

The hosted preview of `tradecraft`.

Deliberately narrow: runs only the four `safe_for_hosted=True` collectors
(`footprint`, `company`, `job`, `github`). For the full collector roster
(news, breaches, m&a, people, business) and the full BYOK AI integration,
install the [local CLI](../README.md).

## Local development

```bash
pnpm install
pnpm dev      # Next.js on http://localhost:3000
# In another shell, to drive the Python Functions:
bash scripts/vendor-tradecraft.sh
vercel dev    # Optional: tests the /api/* endpoints locally
```

## Deploy

This subdirectory is the Vercel project root. Connect the repo in the
Vercel dashboard and set the project root to `web/`. Build command and
runtime config are in `vercel.ts`.

## What goes where

- `app/` — Next.js App Router pages and React components
- `api/compile.py` — Python Function that imports tradecraft and runs the
  hosted-safe collectors
- `api/ai.py` — BYOK AI proxy (provider + key in, response out, key never
  stored or logged)
- `middleware.ts` — Per-IP rate limit on `/api/compile`
- `scripts/vendor-tradecraft.sh` — Build hook: copies `../src/tradecraft/`
  into `api/_vendor/`

## Design

This site uses a deliberately distinctive "Field Dossier" aesthetic — manila
paper, typewriter type, classification stamps. Tokens in `app/globals.css`.
```

- [ ] **Step 2: Append to root `README.md`**

Find the existing `## Install` heading (or similar). Insert a new section AFTER it, BEFORE `## Usage`:

```markdown
## Hosted preview

Try tradecraft without installing anything at the hosted demo (URL filled in
post-deploy). The hosted preview runs only `footprint`, `company`, `job`, and
`github` collectors — by design. For the full collector roster and BYOK AI,
install the CLI above.

Source for the web app is in [`web/`](web/).
```

- [ ] **Step 3: Commit**

```
git add web/README.md README.md
git commit -m "$(cat <<'EOF'
docs(web): web README + root README hosted-preview section

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Deploy to Vercel + smoke test

This task requires the Vercel CLI authenticated to a Vercel account. The session-start hook already recommends `npm i -g vercel`.

- [ ] **Step 1: Authenticate the Vercel CLI (interactive)**

The user runs this themselves at their terminal:

```
! vercel login
```

This opens a browser for OAuth. Wait for completion.

- [ ] **Step 2: Link the project**

From `web/`:

```
cd web
vercel link --yes --project tradecraft-osint
```

This creates `web/.vercel/project.json` (gitignored).

- [ ] **Step 3: First deploy (preview)**

```
cd web
vercel deploy
```

This builds and deploys to a preview URL. Note the URL printed.

- [ ] **Step 4: Smoke test the preview**

Hit the home page in a browser to confirm it loads with the Field Dossier style. Then test the API:

```
curl -X POST https://<preview-url>/api/compile \
  -H "Content-Type: application/json" \
  -d '{"root_url":"https://example.com","company":"Example"}'
```

Expected: JSON dossier with schema_version: 1.

If something's broken (build failure, runtime error, missing dep), check:

```
vercel logs <preview-url>
```

- [ ] **Step 5: Promote to production**

Once the preview looks good:

```
vercel deploy --prod
```

The production URL will be `https://tradecraft-osint.vercel.app` (or whatever the project's primary domain is).

- [ ] **Step 6: Manually verify the production URL**

Open the production URL, run a real dossier against `https://example.com`, confirm the dossier renders.

- [ ] **Step 7: Update root README with the live URL**

In `README.md`, replace the placeholder in the "Hosted preview" section with the actual URL:

```markdown
Try tradecraft without installing anything at https://tradecraft-osint.vercel.app — the
hosted preview runs only `footprint`, `company`, `job`, and `github` collectors by design.
```

- [ ] **Step 8: Commit + push**

```
git add README.md
git commit -m "docs: hosted URL https://tradecraft-osint.vercel.app

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
git push origin main
```

---

## Task 12: Version bump + CHANGELOG + tag v1.1.0

**Files:**
- Modify: `src/tradecraft/__init__.py`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Bump CLI version to 1.1.0**

In `src/tradecraft/__init__.py`, change `__version__ = "0.3.0"` to `__version__ = "1.1.0"`.

Rationale for jumping past 1.0: the user's goal trajectory groups "CLI + hosted web" as the combined milestone. v0.3.0 was the CLI-feature-complete release; v1.1.0 stamps the hosted-preview-complete release. v1.0.0 is implicitly bypassed.

- [ ] **Step 2: CHANGELOG**

In `CHANGELOG.md`, insert AFTER the `## [Unreleased]` line and BEFORE `## [0.3.0]`:

```markdown
## [1.1.0] - 2026-05-30

### Added

- **Hosted preview at https://tradecraft-osint.vercel.app.** Next.js 16 + Tailwind v4
  frontend in `web/`. Single-page web app that submits a target to the
  `safe_for_hosted=True` collectors (footprint, company, job, github) via a
  Vercel Python Function that vendors the tradecraft package at build time.
  Dossier renders inline with a distinctive "Field Dossier" visual style
  (manila paper, typewriter type, classification stamps).
- **BYOK AI proxy at `/api/ai`.** Accepts a provider + key + prompt from the
  browser, calls the provider, returns the response. The key is forwarded
  once and never stored, logged, or written to disk. Supports Anthropic
  (with prompt caching) and any OpenAI-compatible endpoint.
- **Per-IP rate limit on `/api/compile`:** 3 requests / IP / hour, enforced
  in Routing Middleware.

### Versioning note

Jumped from 0.3.0 to 1.1.0 to reflect the "CLI + hosted web" milestone the
project planned for from day one. v1.0.0 is implicitly the CLI-feature-complete
snapshot at tag v0.3.0.
```

- [ ] **Step 3: Verify the package version**

```
uv sync --all-extras
uv run python -c "import tradecraft; print(tradecraft.__version__)"
```

Expected: `1.1.0`.

- [ ] **Step 4: Tag and push**

```
git add src/tradecraft/__init__.py CHANGELOG.md
git commit -m "$(cat <<'EOF'
chore: bump to 1.1.0 + CHANGELOG entry for hosted web

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git tag -a v1.1.0 -m "tradecraft v1.1.0: hosted web preview at tradecraft-osint.vercel.app"
git push origin main
git push origin v1.1.0
gh run watch $(gh run list --branch main --limit 1 --json databaseId -q '.[0].databaseId') --exit-status
```

Expected: CI runs (it only tests the Python package, not the web app — the web app's Vercel deploy is separate). CI should go green.

---

## Self-review (run by the engineer / agent after completing all tasks)

- [ ] The production URL loads with the Field Dossier visual style — manila paper, typewriter headers, no generic shadcn defaults.
- [ ] A real dossier run against a known target renders all four collector sections + questions.
- [ ] The "Deep dive with AI" modal accepts a key and produces a numbered list of additional questions.
- [ ] The 4th submission from the same IP within an hour returns HTTP 429.
- [ ] No browser console errors.
- [ ] `git tag` shows `v0.1.0a0`, `v0.1.0a1`, `v0.2.0`, `v0.3.0`, `v1.1.0`.

---

## Plan-author self-review

**Spec coverage (against `docs/superpowers/specs/2026-05-23-tradecraft-design.md`):**

- §10.1 Hosted runs only `safe_for_hosted=True` collectors → Task 6 (HOSTED_COLLECTORS list of 4) + orchestrator `hosted=True`.
- §10.2 BYOK AI proxied per request, never stored → Task 8 (api/ai.py + AiKeyDialog).
- §10.3 Next.js App Router on Vercel + Python Vercel Function + vercel.ts → Tasks 1, 6, 9.
- §10.3 Per-IP rate limit → Task 9.
- §10.3 Vercel BotID — note: BotID enabled in the Vercel project dashboard post-deploy; no code change needed. Listed in the post-deploy checklist (Task 11 manual step).
- Distinctive frontend (NOT standard Claude site) → Tasks 2, 3, 4 (Field Dossier tokens + components).

**Placeholder scan:** no "TBD" / "TODO" / "Similar to Task N" in code. The "URL filled in post-deploy" in Task 10 step 1 is a deliberate placeholder that Task 11 replaces.

**Type consistency:**
- `Dossier` TypeScript type in `DossierDisplay.tsx` matches the JSON shape returned by `/api/compile` (target, results, questions).
- Provider names in `AiKeyDialog.tsx` (`"anthropic" | "openai"`) match the strings consumed by `api/ai.py`.
- `Question.source_collector === "ai"` partitioning matches the CLI renderer's logic.

**One residual risk:** if `@vercel/config` is not yet published when the implementer runs `pnpm add @vercel/config`, Task 9 calls out the `vercel.json` fallback. The implementer should switch without escalating.
