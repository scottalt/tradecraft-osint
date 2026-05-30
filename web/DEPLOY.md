# Deploying `tradecraft-web`

Two supported paths. Pick one.

---

## Path A: Vercel Deploy Button (fastest, one click)

Click this URL — it pre-fills the import wizard with the right repo and
sets `web/` as the root directory:

**https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fscottalt%2Ftradecraft-osint%2Ftree%2Fmain%2Fweb&project-name=tradecraft-osint**

Sign in if prompted, then click **Deploy**. Build takes ~2 minutes.
The live URL appears in the dashboard.

That's it. No CLI install, no auth dance, no advanced configuration.
The vendored `tradecraft` Python source is already committed at
`web/api/_vendor/tradecraft/`, so no "Include source files outside Root
Directory" toggle is needed.

---

## Path B: GitHub Actions auto-deploy (set up once, deploys forever)

After completing Path A at least once (so a Vercel project exists), wire up
CI/CD so every push to `main` auto-deploys without you having to do anything.

### One-time setup

1. **Generate a Vercel access token:**
   https://vercel.com/account/settings/tokens → Create Token → name it
   `tradecraft-osint github-actions` → copy the value.

2. **Find the Project ID:**
   https://vercel.com/scott-altiparmaks-projects/tradecraft-osint/settings →
   General → copy the value after "Project ID".

3. **Set the three secrets and the enable flag on GitHub:**

   ```bash
   gh secret set VERCEL_TOKEN -b "<paste your token>"
   gh secret set VERCEL_ORG_ID -b "team_YpYW3uhGGb2avxTb8DN1kMe8"
   gh secret set VERCEL_PROJECT_ID -b "<paste your project id>"
   gh variable set ENABLE_VERCEL_DEPLOY -b "true"
   ```

   (Or use the GitHub UI: Settings → Secrets and variables → Actions →
   `New repository secret` × 3, then `Variables` → `New repository
   variable` for the enable flag.)

4. **Trigger the first auto-deploy:**

   ```bash
   gh workflow run deploy-web.yml
   ```

   Or just push any change to `web/`. The workflow at
   `.github/workflows/deploy-web.yml` re-vendors `tradecraft`, builds via
   Vercel CLI, and deploys to production.

### After setup

Every push to `main` that touches `web/`, `src/tradecraft/`, or the
workflow itself auto-deploys. The CI badge in the root README shows the
deploy status alongside test status.

---

## Local dev (no deploy involved)

```bash
cd web
npm install
npm run dev    # http://localhost:3000
```

The Python Functions don't run via `next dev`. To exercise them locally,
install Vercel CLI (`npm i -g vercel`) and run `vercel dev` in a second
shell from the `web/` directory.
