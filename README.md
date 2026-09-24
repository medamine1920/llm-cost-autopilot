# LLM Cost Autopilot

A routing layer that sends each request to the **cheapest model that can answer it reliably** — and proves the routing decisions with measured data rather than assumptions.

Most teams send every request to their most expensive model, paying premium prices for tasks a smaller model handles just as well. This service classifies each prompt, routes it to the right tier, enforces a latency ceiling and a daily spend cap, and reports why every decision was made.

**Live:** `http://91.99.98.217:8000` — ask a question and watch which model answers, why, and what it cost.

> Cost figures use published list pricing (verified 2026-09-20). Development runs on free tiers, so actual spend is $0. The routing logic is price-agnostic: swapping in an enterprise ladder is a config change.

---

## What it does

```
prompt → rules decide the tier → cheapest capable model answers
                                        ↓ on failure or timeout
                                 stronger model (fallback)
```

Every response carries its own explanation:

```json
{
  "text": "...The fuel cost for 340 km is $39.78.",
  "model": "groq-20b",
  "tier": "moderate",
  "cost_usd": 0.00008685,
  "latency_ms": 1871,
  "routing_reason": "6 numbers in prompt: arithmetic risk"
}
```

| Tier | Model | $ / 1M in · out | Chosen when |
|---|---|---|---|
| simple | Llama 3.2 3B (self-hosted) | 0.00 · 0.00 | no risk signals in the prompt |
| moderate | GPT-OSS 20B (Groq) | 0.075 · 0.30 | arithmetic, multi-step logic, nuance, strict format, long output |
| escalation | GPT-OSS 120B (Groq) | 0.15 · 0.60 | reserved — benchmarks showed it was never needed |

---

## How routing decisions were made

The tiers are not guesses. Each prompt in a 140-item dataset was run three times against every model at temperature 0 with a fixed seed, auto-graded against verified answers, and labelled with **the cheapest model that passed all three runs**.

```
golden set → benchmark (3 runs × N models) → grade → tier_report → labels
```

Findings that shaped the design:

- **The 20B model passed every auto-graded prompt, 3/3 — matching the 120B everywhere.** The most expensive tier added no measurable quality, so it was removed from routing. "Always use the best model" was measurably wrong.
- **Cost per task ≠ price per token.** The 120B costs 2× per token but the 20B produced more output tokens; measured cost per task was ~1.4–1.9×. Routing must optimise on measured cost.
- **The cheap model's failure modes are consistent:** multi-step arithmetic, date/time math, arithmetic over lists, multi-condition rules, nuance ("great battery, terrible camera" → *Negative*), format discipline, and one safety over-refusal — it declined to extract a phone number from the user's own sentence.
- **Tighter instructions can move a task down a tier.** Adding "reply with only the name" made the 3B model answer a logic question correctly that it got wrong while explaining.

### Rules vs. a trained classifier

A logistic-regression classifier was trained on the labelled set (14 hand-built features) and compared against the hand-written rules:

| Approach | Generated prompts (5-fold CV) | Hand-written held-out set | Quality-risk errors |
|---|---|---|---|
| **Rules v1** (shipped) | 88 % | 75 % | **1** |
| Logistic regression | 86 % | 75 % | 2 |

Both lost ~12 points on realistic prompts — textbook distribution shift, visible only because 16 prompts were written by hand and kept entirely out of training. The classifier tied on accuracy and made more of the error that matters, so **it was not deployed**. A trained artifact that adds dependencies and opacity for zero measured gain makes the system worse.

### Verification: measured, then rejected

A cascade was built and evaluated — free deterministic checks first, then an LLM judge:

| Layer | Wrong answers caught | False alarms | Cost |
|---|---|---|---|
| Deterministic checks (refusal, format, empty) | 32 of 78 (41 %) | 1 of 143 | free |
| LLM judge (on survivors) | 37 of 38 (97 %) | 0 of 95 | one call |
| **Combined** | **69 of 70 (99 %)** | **1** | |

Excellent detection — and still not worth shipping. Replaying all strategies over the saved benchmark data:

| Strategy | Quality | Cost vs. baseline | Avg latency |
|---|---|---|---|
| always-cloud (what most teams do) | 100 % | — | 543 ms |
| **rules v1** (shipped) | 99 % | **−20 %** | 1117 ms |
| rules + verification | 100 % | +16 % | 1315 ms |
| full cascade | 100 % | +47 % | 4325 ms |

**Verification only pays when the judge is much cheaper than the escalation target.** Here the judge *is* the escalation target, so checking costs as much as answering. On an enterprise ladder (a cheap model judging, an expensive one escalating) the arithmetic reverses — which is exactly when to revisit it.

The single missed failure was not a judging error: the judge returned an empty verdict and the fail-open policy accepted it. That motivated an explicit `fail_open` parameter and a retry.

---

## Operational design

- **Latency ceiling.** A free answer is only worth waiting so long for. Local calls are bounded by a timeout; exceeding it switches the request to the cloud model and records the reason. This turned a 70-second worst case into a guaranteed ceiling.
- **Latency-aware routing.** Prompts likely to produce long answers ("write a function", "explain…") go to the cloud model even when they are easy — on CPU-only hardware the local model generates at ~5 tokens/s. The router optimises two objectives, not one.
- **Daily budget cap.** Once the day's paid spend hits the limit, every request is served by the cheap tier and the response says so. The paid *fallback* is disabled too, so a dead cheap model cannot quietly keep spending.
- **Rate limiting.** 10 requests/minute per IP.
- **Fallback.** If the chosen model fails, the request is retried on the cloud model and the reason is recorded.
- **Persistent request log.** Every request stores its cost *and* what the cloud model would have cost, so savings are computed from data rather than estimated. Prompt text is never stored — only a hash and a character count.

---

## Architecture

```
app/
  main.py              FastAPI: /, /dashboard, /health, /v1/completions, /v1/stats, /v1/budget
  chat.py              visitor-facing chat page (self-contained HTML)
  dashboard.py         operator stats page
  router.py            choose_tier(), Router, BudgetTracker
  verify.py            deterministic checks + LLM judge
  features.py          prompt → numeric features (classifier experiment)
  store.py             SQLite request log
  config.py            settings from environment
  models/
    registry.py        loads and validates models.yaml
    models.yaml        models, list prices, tier mapping
  providers/           base interface + groq, ollama, gemini
data/                  golden datasets and labels (versioned)
scripts/               benchmark, grading, tier report, prompt generator, simulations
tests/                 health, routing rules, budget cap, config validation, store
.github/workflows/     CI/CD pipeline
INCIDENTS.md           production incidents: symptom, evidence, root cause, fix
```

**Provider abstraction.** One interface — `send(prompt, config) -> Response` — with Groq, Ollama and Gemini implementations. The router imports none of them; providers are injected, which is also why tests run with no network and no API keys. When Gemini became unavailable from the development region mid-build, nothing else changed.

**Config over code.** Models, prices and the tier mapping live in `models.yaml`, validated at startup (a typo crashes the app at boot, not on the first request that needs it). Operators can override the file on the server with a read-only mount and `MODELS_CONFIG_PATH` — swapping models needs no rebuild. Verified in production.

---

## Deployment

```
git push → test → build image → ghcr.io (:latest + :sha) → SSH deploy → smoke test /health
```

Each stage gates the next: a failing test produces no image, and no image means no deploy. The server never builds — it pulls the image CI tested, so what ran in CI is byte-for-byte what serves traffic, and rollback is pulling an older SHA.

- **Host:** Hetzner CX23 (2 vCPU, 4 GB RAM), Docker Compose running the API and Ollama. Ollama has no published port — it is reachable only by the API over Docker's internal network.
- **Security:** non-root container, key-only SSH with root login disabled, ufw, admin access over a private WireGuard mesh, a dedicated deploy key held only in CI secrets. Secrets are never committed; GitHub push protection caught one attempt, which was resolved by rewriting history and rotating the key.
- **State:** SQLite on a Docker volume, so stats and the budget survive deploys.

Measured: Groq ~0.6 s (laptop) / ~1.9 s (server); local model ~6.5 s laptop, ~8–16 s on 2 CPU cores. The free tier's real cost is latency, not money.

---

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                                  # add GROQ_API_KEY
ollama pull llama3.2:3b
docker compose up --build                             # or: uvicorn app.main:app --reload
```

Tests need no keys and no network — providers are faked:

```bash
python -m pytest -v
```

Reproduce the evaluation:

```bash
python -m scripts.benchmark                                   # 3 runs
python -m scripts.tier_report results/<r1>.json results/<r2>.json results/<r3>.json
python -m scripts.train_classifier                            # rules vs. model
python -m scripts.simulate_strategies results/<r1>.json       # cost/quality/latency by strategy
```

---

## Deploying against an enterprise model ladder

The system was built so a company's own models drop in without code changes:

1. Put your models and list prices in `models.yaml` (e.g. `gpt-4o-mini` as the cheap tier, `gpt-4o` as the escalation target).
2. Export a sample of real production prompts into a golden file with verified answers.
3. Run the benchmark three times; `tier_report` labels each prompt with the cheapest reliable model.
4. Route on that evidence — and revisit verification, which becomes profitable once the judge is far cheaper than the escalation target.

The numbers in this README are a demonstration. The method is the transferable part.

---

## Honest limitations

- **The savings figure reflects a deliberately hard dataset.** The benchmark was built to find the cheap model's limits, so roughly half the prompts are hard. Real traffic is usually easier, which would likely increase savings — but the current number is not representative of production traffic, and the live dashboard shows only test traffic so far.
- **Baseline cost is a counterfactual.** It uses the actual answer's token counts; the cloud model would have produced a slightly different number of tokens.
- **Rules are conservative by design.** Some prompts the cheap model could handle still go to the paid tier. A wrong "cheap" costs quality; a wrong "paid" costs a fraction of a cent.
- **Evaluation set is 140 prompts + 16 hand-written.** Conclusions are directional, and per-fold accuracy varied by 16 points.
- **Rate limiting reads the client IP directly.** Behind a reverse proxy it must read `X-Forwarded-For`.
- **Gemini is implemented but unavailable** from the development region; excluded from all benchmarks.

---

## Roadmap

- [x] Deployment-first foundation: CI/CD, hardened VPS, automated deploys
- [x] Provider abstraction, validated config, model registry with verified pricing
- [x] Benchmark harness, golden datasets, automated grading, evidence-based tiers
- [x] Router with fallback, rate limiting, daily budget cap, latency ceiling
- [x] Classifier experiment — measured against the rules baseline, not shipped
- [x] Verification cascade — measured, rejected on economics, documented
- [x] Persistent request log, `/v1/stats`, savings dashboard, visitor chat page
- [ ] Token streaming, so perceived latency drops to under a second
- [ ] Free-judge experiment: if the local model can judge reliably, verification becomes free and the cascade economics change
- [ ] Domain + HTTPS via a reverse proxy
- [ ] Escalation failures fed back as new labelled evaluation cases
