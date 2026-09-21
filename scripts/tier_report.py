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

    counts = defaultdict(lambda: [0, 0])      # prompt_id -> [passed, graded]

    for path in files:
        results = json.loads(Path(path).read_text(encoding="utf-8"))
        for r in results:
            if r["model"] == "ollama-local" and r.get("passed") is not None:
                counts[r["prompt_id"]][1] += 1
                if r["passed"]:
                    counts[r["prompt_id"]][0] += 1

    if not counts:
        print("No graded ollama-local rows found.")
        return

    print(f"{'prompt':<26}{'passed':>8}   suggested tier")
    for prompt_id, (passed, graded) in counts.items():
        tier = "simple" if passed == graded else "moderate"
        print(f"{prompt_id:<26}{f'{passed}/{graded}':>8}   {tier}")


if __name__ == "__main__":
    main()