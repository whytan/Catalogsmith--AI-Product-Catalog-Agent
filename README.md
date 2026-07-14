# Catalogsmith

AI catalog agent that turns messy seller input into storefront-ready listings —
with a **human approval gate**, feedback memory, four-layer guardrails, and an
MCP publish boundary.

**Scale honesty:** built for a 1–2 user demo on SQLite. Not a multi-tenant
marketplace backend. That constraint is intentional.

> **Loop 2 is SYNTHETIC** (simulated personas). It demonstrates a closed-loop
> mechanism only — never a resume metric or shopper-engagement claim.

---

## Why it exists

Sellers paste incomplete facts and expect clean listings. Untethered agents
hallucinate specs, ignore brand voice, and skip review. Catalogsmith forces a
**gate**, remembers **checkable** seller feedback across products, and only
writes the catalog through a fixed storefront tool contract.

---

## Evidence (not vibes)

| Claim | Evidence |
|-------|----------|
| Feedback memory reduces rubric-gated redrafts | Azure ablation (`gpt-5.3-chat`), **N=10**: mean edit rate **1.50 → 0.70**; **7 of 10** products improved, **0** regressed — see [`data/ablation_report.json`](data/ablation_report.json) (`mode=azure`) |
| Unit economics | ~**$0.001** per published listing amortized from the `runs` table |
| Guardrails | Input sanitize · structural validate · grounding check · human gate; CI + **30** golden parse cases + injection traps |

Learning claim scope: **checkable style rules** (length, punctuation, banned
phrases) — not fuzzy taste (“casual tone”) and not real-customer conversion.

Offline `--llm-mock` ablation is a **plumbing / CI check only**. Do not cite
mock means as learning proof.

---

## Loop 1 — seller pipeline

```
sanitize → parse → validate → [facts gate if needed]
  → retrieve (Chroma) → draft → ground-check → gate → MCP publish
```

| Step | What happens |
|------|----------------|
| Sanitize | Strip prompt-injection noise from pasted text |
| Parse / validate | Structure facts; pause for price/category when missing |
| Retrieve | Voice rules + category feedback memories |
| Draft | Azure (or mock) description grounded in facts |
| Gate | Approve / reject+comment / edit — nothing publishes without sign-off |
| Publish | 9-tool MCP storefront boundary |

Reject and edit comments are stored in Chroma so later same-category drafts can
pre-comply. Use `CHROMA_EPHEMERAL=0` so memory survives process restart.

---

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11+ |
| API / UI | FastAPI, Jinja2, WebSockets, vanilla JS |
| Orchestration | LangGraph + SQLite checkpoints |
| LLM | Azure OpenAI (`gpt-5.3-chat`; Responses API for GPT-5.x) |
| Memory | ChromaDB (voice rules + feedback) |
| Catalog | SQLite + SQLAlchemy 2 (async) |
| Boundary | MCP storefront — inline dispatch by default; `catalogsmith-mcp` for stdio |
| Tests | pytest · httpx · CI on push |

---

## Quick start

```powershell
cd "CATALOG AGENT"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
# Or: .\scripts\repair-venv.ps1
copy .env.example .env
# Set AZURE_OPENAI_* and prefer CHROMA_EPHEMERAL=0 for persistence
python run.py
```

`python run.py` boots `src/` onto the path and starts Uvicorn. Prefer it over
calling `uvicorn agent.main:app` directly when the editable install is flaky.

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/app | Agent console (Loop 1) |
| http://127.0.0.1:8000/ | Demo storefront |
| http://127.0.0.1:8000/dashboard/learning | Edit-rate graph (real gate approvals) |
| http://127.0.0.1:8000/insights | SYNTHETIC customer insights (Loop 2) |
| http://127.0.0.1:8000/about | How it works |

CLI helpers:

```powershell
python -m agent.cli.add "Aurora Earbuds, Rs 2499, electronics, 8-hour battery, ANC" -y
python -m agent.cli.panel --limit 5
catalogsmith-mcp
pytest -q
```

---

## Reproduce the learning proof

```powershell
# Persistence smoke test (requires CHROMA_EPHEMERAL=0)
python scripts/check_memory_persistence.py

# Real Azure — LLM_MOCK=0, no mid-run restart
python scripts/run_ablation.py

# Offline plumbing-only (label report mode=mock — not proof)
python scripts/run_ablation.py --llm-mock

# Cost rollup from runs
python scripts/cost_summary.py
```

Primary artifact: [`data/ablation_report.json`](data/ablation_report.json)

---

## Loop 2 — SYNTHETIC customers

Four personas (bargain hunter, spec reader, skeptical gifter, skimmer) browse
published listings, emit views/questions/reviews/cart signals, and feed a theme
miner. Rewrite proposals route through the **same seller gate** as Loop 1.

On `/insights`, use **Run Loop 2 → open gate** for the integrated demo
(panel → mine → rewrite → `/app?thread=…`).

All Loop 2 data is labelled **SYNTHETIC**. Do not treat signal counts or
“questions reduced” as product metrics.

---

## Tests & CI

```powershell
pytest -q
```

GitHub Actions runs the suite with `LLM_MOCK=1`. A second job sets
`SANITIZER_WEAK=1` and expects injection traps to fail — documenting that
guardrails are load-bearing, not decorative.

---

## Non-goals

- Postgres, multi-user auth, SSO  
- Production traffic or SLA claims  
- Using Loop 2 numbers as evidence of real shopper impact  

SQLite + the scale honesty line keep the project defensible in review.

---

## License

MIT
