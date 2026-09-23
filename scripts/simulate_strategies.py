"""Replay saved benchmark data under four routing strategies and compare them.

Run: python -m scripts.simulate_strategies results\\<v3_run>.json results\\<hw_run>.json

Judge calls are cached in data/judge_cache.json, so the first run costs a few
cheap calls and later runs are free and instant.
"""

import asyncio
import json
import sys
from pathlib import Path

from app.config import get_settings
from app.models.registry import REGISTRY
from app.providers.groq import GroqProvider
from app.router import choose_tier
from app.verify import judge, verify

PROMPT_SOURCES = ["data/golden_v3.json", "data/handwritten_v1.json"]
CACHE_PATH = Path("data/judge_cache.json")
LOCAL, CLOUD = "ollama-local", "groq-20b"
JUDGE_MODEL = "groq-20b"
FAIL_OPEN = False          # unparseable verdict → escalate (safer, costs one call)


def load_prompts() -> dict[str, str]:
    prompts = {}
    for path in PROMPT_SOURCES:
        for item in json.loads(Path(path).read_text(encoding="utf-8")):
            prompts[item["id"]] = item["text"]
    return prompts


def load_rows(files: list[str]) -> dict[str, dict[str, dict]]:
    """prompt_id -> model -> row (first run wins; runs are seeded and near-identical)."""
    rows: dict[str, dict[str, dict]] = {}
    for path in files:
        for r in json.loads(Path(path).read_text(encoding="utf-8")):
            if r.get("passed") is None:
                continue                       # manual items: no ground truth
            rows.setdefault(r["prompt_id"], {}).setdefault(r["model"], r)
    return {pid: m for pid, m in rows.items() if LOCAL in m and CLOUD in m}


async def judge_all(cases: list[tuple[str, str, str]]) -> dict[str, dict]:
    """Judge each (prompt_id, prompt, answer) that isn't cached yet."""
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    todo = [c for c in cases if c[0] not in cache]
    if todo:
        print(f"Judging {len(todo)} answers (cached: {len(cache)})...")
        provider = GroqProvider(api_key=get_settings().groq_api_key)
        config = REGISTRY[JUDGE_MODEL]
        for i, (pid, prompt, answer) in enumerate(todo, 1):
            before = None
            try:
                response = await provider.send(
                    "", config) if False else None          # placeholder, unused
            finally:
                pass
            ok, reason = await judge(prompt, answer, provider, config, fail_open=FAIL_OPEN)
            # cost/latency of the judge call: approximate from the model's own pricing
            cache[pid] = {"ok": ok, "reason": reason}
            if i % 10 == 0:
                print(f"  {i}/{len(todo)}")
            await asyncio.sleep(2.5)
        CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return cache


def verify_chain(prompt: str, answer: str, judged: dict) -> tuple[bool, int]:
    """Returns (answer_accepted, judge_calls_used)."""
    ok, _ = verify(prompt, answer)
    if not ok:
        return False, 0                        # caught for free
    verdict = judged.get("ok", True)
    return verdict, 1


def simulate(rows, prompts, cache, judge_cost, judge_latency):
    strategies = {name: {"cost": 0.0, "latency": 0, "passed": 0, "escalated": 0}
                  for name in ("always-cloud", "rules v1", "rules + checks","rules + verify", "full cascade")}
    n = len(rows)

    for pid, by_model in rows.items():
        prompt = prompts[pid]
        local, cloud = by_model[LOCAL], by_model[CLOUD]

        # 1. always-cloud
        s = strategies["always-cloud"]
        s["cost"] += cloud["cost_usd"]
        s["latency"] += cloud["latency_ms"]
        s["passed"] += cloud["passed"]

        # 2. rules v1 (what is live today)
        tier = choose_tier(prompt)[0]
        chosen = local if tier == "simple" else cloud
        s = strategies["rules v1"]
        s["cost"] += chosen["cost_usd"]
        s["latency"] += chosen["latency_ms"]
        s["passed"] += chosen["passed"]
        
        # 3b. rules + free checks only (no judge)
        s = strategies["rules + checks"]
        if tier != "simple":
            s["cost"] += cloud["cost_usd"]
            s["latency"] += cloud["latency_ms"]
            s["passed"] += cloud["passed"]
        else:
            ok, _ = verify(prompt, local["text"])
            s["cost"] += local["cost_usd"]
            s["latency"] += local["latency_ms"]
            if ok:
                s["passed"] += local["passed"]
            else:
                s["escalated"] += 1
                s["cost"] += cloud["cost_usd"]
                s["latency"] += cloud["latency_ms"]
                s["passed"] += cloud["passed"]

        # 3. rules + verification on the cheap path
        s = strategies["rules + verify"]
        if tier != "simple":
            s["cost"] += cloud["cost_usd"]
            s["latency"] += cloud["latency_ms"]
            s["passed"] += cloud["passed"]
        else:
            accepted, judge_calls = verify_chain(prompt, local["text"], cache.get(pid, {}))
            s["cost"] += local["cost_usd"] + judge_calls * judge_cost
            s["latency"] += local["latency_ms"] + judge_calls * judge_latency
            if accepted:
                s["passed"] += local["passed"]
            else:
                s["escalated"] += 1
                s["cost"] += cloud["cost_usd"]
                s["latency"] += cloud["latency_ms"]
                s["passed"] += cloud["passed"]

        # 4. full cascade: everything starts on the cheap model
        s = strategies["full cascade"]
        accepted, judge_calls = verify_chain(prompt, local["text"], cache.get(pid, {}))
        s["cost"] += local["cost_usd"] + judge_calls * judge_cost
        s["latency"] += local["latency_ms"] + judge_calls * judge_latency
        if accepted:
            s["passed"] += local["passed"]
        else:
            s["escalated"] += 1
            s["cost"] += cloud["cost_usd"]
            s["latency"] += cloud["latency_ms"]
            s["passed"] += cloud["passed"]

    return strategies, n


async def main() -> None:
    files = sys.argv[1:]
    if not files:
        print("Usage: python -m scripts.simulate_strategies <result files...>")
        return

    prompts = load_prompts()
    rows = load_rows(files)
    print(f"{len(rows)} prompts with both local and cloud answers")

    # judge only the local answers that pass the free checks
    cases = []
    for pid, by_model in rows.items():
        answer = by_model[LOCAL]["text"]
        if verify(prompts[pid], answer)[0]:
            cases.append((pid, prompts[pid], answer))
    cache = await judge_all(cases)

    # cost/latency of one judge call, from the cloud rows themselves
    cloud_rows = [m[CLOUD] for m in rows.values()]
    judge_cost = sum(r["cost_usd"] for r in cloud_rows) / len(cloud_rows)
    judge_latency = int(sum(r["latency_ms"] for r in cloud_rows) / len(cloud_rows))
    print(f"Judge call assumed at ${judge_cost:.6f} / {judge_latency} ms (cloud average)\n")

    strategies, n = simulate(rows, prompts, cache, judge_cost, judge_latency)

    baseline = strategies["always-cloud"]["cost"]
    print(f"{'strategy':<18}{'quality':>9}{'cost':>12}{'vs base':>10}{'avg ms':>9}{'escalated':>11}")
    for name, s in strategies.items():
        saving = (1 - s["cost"] / baseline) if baseline else 0
        print(f"{name:<18}{s['passed'] / n:>8.0%}{s['cost']:>12.6f}{saving:>9.0%}"
              f"{s['latency'] // n:>9}{s['escalated']:>11}")

    print(f"\nPer 1,000 requests at these rates:")
    for name, s in strategies.items():
        print(f"  {name:<18} ${s['cost'] / n * 1000:.4f}")


if __name__ == "__main__":
    asyncio.run(main())