# Popper — web demo + Claude agent

An interactive site for [Popper](../README.md): the trust ladder, live audit results, and a
**Claude agent** that reasons the Popper way (falsify first) and runs the **Axiom Lean Engine
(AXLE)** live from the browser.

The agent is general-purpose Claude (Opus 4.8) — ask it any math or coding question. Its system
prompt (`app/api/chat/route.ts`) makes the **Popper method its default**: for checkable claims it
calls `disprove_lean` (AXLE) and reports the real counterexample instead of just asserting, and it
distinguishes *verified* vs *falsified* vs *not-falsified*.

## Architecture

```
app/
  page.tsx                hero + trust ladder + dashboard + chat
  components/             Ladder, Dashboard (tabs over results), Chat (agent UI)
  lib/axle.ts             TypeScript client for AXLE REST (POST /api/v1/{check,disprove})
  lib/results.ts          imports the precomputed results JSON (in app/data/)
  api/chat/route.ts       the Claude agent: tool-use loop with disprove_lean / check_lean / get_audit_results
```

The agent's tools:
- **`disprove_lean`** → `POST https://axle.axiommath.ai/api/v1/disprove` (property-based falsification via `plausible`)
- **`check_lean`** → `POST .../api/v1/check`
- **`get_audit_results`** → the committed JSON in `app/data/`

## Run locally

```bash
cd web
cp .env.example .env.local        # then fill in the two keys
npm install
npm run dev                        # http://localhost:3000
```

`.env.local`:

```
ANTHROPIC_API_KEY=sk-ant-...       # the chatbot (Claude)
AXLE_API_KEY=pk_...                # the live disprove/check tools (https://axle.axiommath.ai/app/console)
# optional: ANTHROPIC_MODEL (default claude-opus-4-8), AXLE_ENVIRONMENT (default lean-4.28.0)
```

## Deploy to Vercel

1. Push this repo to GitHub (already done).
2. In Vercel: **New Project → import the repo → set Root Directory to `web/`**.
3. Add Environment Variables `ANTHROPIC_API_KEY` and `AXLE_API_KEY` (Production + Preview).
4. Deploy.

Or from the CLI:

```bash
cd web
npx vercel            # link/create the project
npx vercel env add ANTHROPIC_API_KEY
npx vercel env add AXLE_API_KEY
npx vercel --prod
```

**Notes**
- The chat route sets `maxDuration = 60`. Lean checks that pull in Mathlib can be slow; on the
  Vercel Hobby plan, function duration is capped (raise it on Pro). The agent uses
  `ignore_imports` so core-Lean statements stay fast.
- Keys live only in Vercel env vars / `.env.local` — never commit them (`.env*` is git-ignored).
