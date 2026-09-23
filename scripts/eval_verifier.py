"""Measure the deterministic verifier against benchmark ground truth.

Run: python -m scripts.eval_verifier results\\<run>.json [more runs...]
Uses the ollama-local answers: for each one, did verify() agree with the grader?
"""

import json
import sys
from collections import Counter
from pathlib import Path

from app.verify import verify

PROMPT_SOURCES = ["data/golden_v3.json", "data/handwritten_v1.json"]


def load_prompts() -> dict[str, str]:
    prompts = {}
    for path in PROMPT_SOURCES:
        for item in json.loads(Path(path).read_text(encoding="utf-8")):
            prompts[item["id"]] = item["text"]
    return prompts


def main() -> None:
    prompts = load_prompts()
    tally = Counter()
    reasons = Counter()
    missed, false_alarms = [], []

    for path in sys.argv[1:]:
        for r in json.loads(Path(path).read_text(encoding="utf-8")):
            if r["model"] != "ollama-local" or r.get("passed") is None:
                continue
            prompt = prompts.get(r["prompt_id"])
            if prompt is None:
                continue
            ok, reason = verify(prompt, r.get("text", ""))
            truth = r["passed"]

            if not truth and not ok:
                tally["caught"] += 1
                reasons[reason] += 1
            elif not truth and ok:
                tally["missed"] += 1
                missed.append((r["prompt_id"], r["text"]))
            elif truth and not ok:
                tally["false_alarm"] += 1
                false_alarms.append((r["prompt_id"], reason, r["text"]))
            else:
                tally["clean_pass"] += 1

    wrong = tally["caught"] + tally["missed"]
    print(f"Local-model answers checked: {sum(tally.values())}")
    print(f"  wrong answers:  {wrong}")
    print(f"    caught by verifier:   {tally['caught']}")
    print(f"    missed (quality risk): {tally['missed']}")
    print(f"  correct answers flagged anyway (false alarms): {tally['false_alarm']}")
    if wrong:
        print(f"\nCatch rate: {tally['caught'] / wrong:.0%}")
    print(f"\nWhat the catches were: {dict(reasons)}")

    print("\nMissed failures (well-formed but wrong):")
    for pid, text in missed[:15]:
        print(f"  {pid:<24} {text.strip()[:70]!r}")

    print("\nFalse alarms:")
    for pid, reason, text in false_alarms[:15]:
        print(f"  {pid:<24} [{reason}] {text.strip()[:60]!r}")


if __name__ == "__main__":
    main()