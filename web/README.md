# tradecraft-web

The hosted preview of `tradecraft`.

Deliberately narrow: runs only the four `safe_for_hosted=True` collectors
(`footprint`, `company`, `job`, `github`). For the full collector roster
(news, breaches, m&a, people, business) and the full BYOK AI integration,
install the [local CLI](../README.md).

## Local development

```bash
npm install
npm run dev    # Next.js on http://localhost:3000
# In another shell, to drive the Python Functions:
bash scripts/vendor-tradecraft.sh
vercel dev     # Optional: tests the /api/* endpoints locally
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
  stored or logged; user-supplied base_url validated against SSRF)
- `middleware.ts` — Per-IP rate limit on `/api/compile`
- `scripts/vendor-tradecraft.sh` — Build hook: copies `../src/tradecraft/`
  into `api/_vendor/`

## Design

This site uses a deliberately distinctive "Field Dossier" aesthetic — manila
paper, typewriter type, classification stamps. Tokens in `app/globals.css`.
