"""Benchmark every registry model against a fixed prompt set.

Run from project root:  python -m scripts.benchmark
"""
import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from statistics import mean
from scripts.grading import grade
from app.config import get_settings
from app.models.registry import REGISTRY
from app.providers.base import Provider
from app.providers.groq import GroqProvider
from app.providers.ollama import OllamaProvider

parser = argparse.ArgumentParser()
parser.add_argument("--golden", default="data/golden_v3.json")
GOLDEN_PATH = Path(parser.parse_args().golden)

SKIP_MODELS = {"groq-120b"}

def load_golden() -> list[dict]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def build_providers() -> dict[str, Provider]:
    settings = get_settings()
    return {
        "groq": GroqProvider(api_key=settings.groq_api_key),
        "ollama": OllamaProvider(),
    }
    
async def run_one(provider: Provider, model_key: str, item: dict) -> dict:
    config = REGISTRY[model_key]
    base = {"model": model_key, "prompt_id": item["id"], "tier_label": item["tier_label"]}
    try:
        response = await provider.send(item["text"], config)
        return {**base, "ok": True, **response.model_dump()}
    except Exception as exc:
        return {**base, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
        
        
async def main() -> None:
    providers = build_providers()
    models = [k for k, cfg in REGISTRY.items() if cfg.provider in providers and k not in SKIP_MODELS]

    golden = load_golden()

    print("Warming up Ollama...")
    await run_one(providers["ollama"], "ollama-local", golden[0])

    results = []
    for item in golden:
        for model_key in models:
            config = REGISTRY[model_key]
            result = await run_one(providers[config.provider], model_key, item)
            if result["ok"]:
                result["passed"] = grade(result["text"], item)
            results.append(result)

            mark = {True: "PASS", False: "FAIL", None: "manual"}.get(result.get("passed"), "ERROR")
            print(f"{item['id']:<24} {model_key:<14} {mark}")

            if config.provider == "groq":
                await asyncio.sleep(2.5)


    save_results(results)              
    print_summary(results, models)


def save_results(results: list[dict]) -> None:      
    out_dir = Path("results")
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"benchmark_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved {len(results)} results to {path}")


def print_summary(results: list[dict], models: list[str]) -> None:
    print(f"\n{'model':<14}{'passed':>9}{'avg_ms':>9}{'avg_in':>8}{'avg_out':>9}{'total_$':>12}")
    for model_key in models:
        rows = [r for r in results if r["model"] == model_key and r["ok"]]
        if not rows:
            print(f"{model_key:<14}  all calls failed")
            continue
        graded = [r for r in rows if r.get("passed") is not None]
        passed = sum(1 for r in graded if r["passed"])
        print(f"{model_key:<14}{f'{passed}/{len(graded)}':>9}"
              f"{mean(r['latency_ms'] for r in rows):>9.0f}"
              f"{mean(r['input_tokens'] for r in rows):>8.0f}"
              f"{mean(r['output_tokens'] for r in rows):>9.0f}"
              f"{sum(r['cost_usd'] for r in rows):>12.6f}")


if __name__ == "__main__":
    asyncio.run(main())