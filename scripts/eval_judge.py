"""Measure the LLM judge against benchmark ground truth.

Run: python -m scripts.eval_judge results\\<run>.json [more runs...]

Only answers that already passed the free deterministic checks are judged —
that is exactly where the judge sits in the cascade.
"""

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from app.config import get_settings
from app.models.registry import REGISTRY
from app.providers.groq import GroqProvider
from app.verify import judge, verify

PROMPT_SOURCES = ["data/golden_v3.json", "data/handwritten_v1.json"]
JUDGE_MODEL = "groq-20b"
THROTTLE_SECONDS = 2.5


def load_prompts() -> dict[str, str]:
    prompts = {}
    for path in PROMPT_SOURCES:
        for item in json.loads(Path(path).read_text(encoding="utf-8")):
            prompts[item["id"]] = item["text"]
    return prompts


async def main() -> None:
    files = sys.argv[1:]
    if not files:
        print("Usage: python -m scripts.eval_judge <result files...>")
        return

    prompts = load_prompts()
    provider = GroqProvider(api_key=get_settings().groq_api_key)
    config = REGISTRY[JUDGE_MODEL]

    tally = Counter()
    judge_cost = 0.0
    missed, false_alarms, unclear = [], [], []

    for path in files:
        for r in json.loads(Path(path).read_text(encoding="utf-8")):
            if r["model"] != "ollama-local" or r.get("passed") is None:
                continue

            prompt = prompts.get(r["prompt_id"])
            if prompt is None:
                continue

            answer = r.get("text", "")
            if not verify(prompt, answer)[0]:
                tally["caught_free"] += 1          # already handled by free checks
                continue

            ok, reason = await judge(prompt, answer, provider, config)
            truth = r["passed"]

            if "unclear" in reason:
                unclear.append((r["prompt_id"], reason))

            if not truth and not ok:
                tally["caught"] += 1
            elif not truth and ok:
                tally["missed"] += 1
                missed.append((r["prompt_id"], answer.strip()[:60]))
            elif truth and not ok:
                tally["false_alarm"] += 1
                false_alarms.append((r["prompt_id"], answer.strip()[:60]))
            else:
                tally["clean_pass"] += 1

            await asyncio.sleep(THROTTLE_SECONDS)

    judged = tally["caught"] + tally["missed"] + tally["false_alarm"] + tally["clean_pass"]
    wrong = tally["caught"] + tally["missed"]

    print(f"\nCaught for free before the judge: {tally['caught_free']}")
    print(f"Answers sent to the judge:        {judged}")
    print(f"  wrong answers among them: {wrong}")
    print(f"    caught by judge:        {tally['caught']}")
    print(f"    missed (quality risk):  {tally['missed']}")
    print(f"  correct answers flagged (false alarms): {tally['false_alarm']}")
    if wrong:
        print(f"\nJudge catch rate: {tally['caught'] / wrong:.0%}")
    if judged:
        print(f"False alarm rate: {tally['false_alarm'] / judged:.0%} of judged answers")

    print("\nMissed by the judge (wrong, accepted):")
    for pid, ans in missed[:15]:
        print(f"  {pid:<26} {ans!r}")

    print("\nFalse alarms (correct, rejected):")
    for pid, ans in false_alarms[:15]:
        print(f"  {pid:<26} {ans!r}")

    if unclear:
        print(f"\nUnparseable verdicts (accepted by default): {len(unclear)}")
        for pid, reason in unclear[:5]:
            print(f"  {pid:<26} {reason}")


if __name__ == "__main__":
    asyncio.run(main())