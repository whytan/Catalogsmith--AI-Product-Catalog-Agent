# Catalogsmith

**v1 + Loop 2 complete (Weekends 1–8).** An AI catalog agent that turns raw product facts into published,
storefront-ready listings — with a human approval gate, feedback memory, four-layer guardrails,
MCP storefront boundary, and a **SYNTHETIC** customer feedback loop.

**Scale honesty:** 1–2 users, SQLite, one `docker compose up`. Stated plainly.

> **SYNTHETIC Loop 2 data is simulated customer feedback. It never counts toward resume metrics.**

---

## Quick start

```powershell
cd "CATALOG AGENT"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\repair-venv.ps1
copy .env.example .env
python run.py
```

Or:

```powershell
.\scripts\run.ps1
```

`python run.py` bootstraps `src/` on the path and starts uvicorn — it works even when pip editable install is broken. **Avoid** `uvicorn agent.main:app` directly.

| URL | What |
|-----|------|
| http://localhost:8000/app | Agent console (Loop 1) |
| http://localhost:8000/dashboard/learning | Edit-rate graph |
| http://localhost:8000/dashboard/personas | **SYNTHETIC** persona signals |
| http://localhost:8000/dashboard/loop2 | Signal mining + rewrite loop |

---

## Loop 1 (seller) — Weekends 1–6

Paste facts → sanitize → parse → validate → retrieve (Chroma) → draft → ground-check → **gate** → publish via MCP.

```powershell
python -m agent.cli.add "Aurora Earbuds, Rs 2499, electronics, 8-hour battery, ANC" -y
catalogsmith-mcp   # 9-tool MCP server for Claude Desktop
pytest             # 30 golden cases + 10 injection traps
```

---

## Loop 2 (customers) — Weekends 7–8

Published listing → **SYNTHETIC persona panel** → signal miner → rewrite proposal → **same gate** → listing updated.

### Weekend 7 — Persona panel

Four personas: bargain hunter, spec reader, skeptical gifter, skimmer.

```powershell
catalogsmith-panel
# or: python -m agent.cli.panel --limit 5
# API: POST /api/personas/panel/run
```

Signals land in `/dashboard/personas` (views, questions, reviews, cart clicks). All labelled **SYNTHETIC**.

### Weekend 8 — Signal mining → rewrite

```powershell
# Preview rewrite proposal
python -m agent.cli.panel --rewrite-product 1 --theme battery

# Start rewrite through the human gate
# POST /api/personas/rewrite/1/start?theme=battery
# Then approve at /app gate (thread_id returned)
```

- Miner clusters questions per product (`battery`, `price`, `specs`, …)
- Rewrite proposal routes through the **same gate** as Loop 1
- Loop conflicts surfaced when seller style ≠ persona preferences (`/dashboard/loop2`)

---

## Architecture

```
Loop 1: seller input → pipeline → gate → MCP publish
Loop 2: published listing → SYNTHETIC personas → signals → miner → rewrite → gate → MCP update
```

---

## Weekend delivery log

| Weekend | Deliverable |
|---------|-------------|
| 1–6 | v1: storefront, agent, memory, guardrails, CI, MCP ✅ |
| 7 | SYNTHETIC persona panel + signals dashboard ✅ |
| 8 | Signal mining, rewrite gate, loop conflicts ✅ |

---

## License

MIT
