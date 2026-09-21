"""Count ollama-local pass rates across benchmark runs and suggest tiers.

Run: python -m scripts.tier_report results\\file1.json results\\file2.json ...
"""

import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> None:
    files = sys.argv[1:]
    if not files:
        print("Usage: python -m scripts.tier_report <result files...>")
        return

    counts = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # prompt->model->[passed, graded]

    for path in files:
        for r in json.loads(Path(path).read_text(encoding="utf-8")):
            if r.get("passed") is not None:
                c = counts[r["prompt_id"]][r["model"]]
                c[1] += 1
                c[0] += r["passed"]

    def reliable(prompt_id: str, model: str) -> bool:
        passed, graded = counts[prompt_id][model]
        return graded > 0 and passed == graded

    print(f"{'prompt':<26}{'local':>7}{'20b':>7}{'120b':>7}   tier")
    for prompt_id, by_model in counts.items():
        cells = [f"{by_model[m][0]}/{by_model[m][1]}" for m in ("ollama-local", "groq-20b", "groq-120b")]
        if reliable(prompt_id, "ollama-local"):
            tier = "simple"
        elif reliable(prompt_id, "groq-20b"):
            tier = "moderate"
        elif reliable(prompt_id, "groq-120b"):
            tier = "complex"
        else:
            tier = "UNSOLVED"
        print(f"{prompt_id:<26}{cells[0]:>7}{cells[1]:>7}{cells[2]:>7}   {tier}")


if __name__ == "__main__":
    main()