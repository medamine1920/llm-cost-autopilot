"""Aggregate benchmark runs and label each prompt with the cheapest reliable tier.

Run:
  python -m scripts.tier_report <result files...>                       → data/labels_v3.json
  python -m scripts.tier_report <result files...> --out <labels file>   → custom path
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

MODELS = ("ollama-local", "groq-20b", "groq-120b")
DEFAULT_OUT = Path("data/labels_v3.json")


def parse_args(argv: list[str]) -> tuple[list[str], Path]:
    args = list(argv)
    out_path = DEFAULT_OUT
    if "--out" in args:
        i = args.index("--out")
        out_path = Path(args[i + 1])
        del args[i:i + 2]
    return args, out_path


def main() -> None:
    files, out_path = parse_args(sys.argv[1:])
    if not files:
        print("Usage: python -m scripts.tier_report <result files...> [--out path]")
        return

    # prompt -> model -> [passed, graded]
    counts = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for path in files:
        for r in json.loads(Path(path).read_text(encoding="utf-8")):
            if r.get("passed") is not None:
                c = counts[r["prompt_id"]][r["model"]]
                c[1] += 1
                c[0] += int(r["passed"])

    if not counts:
        print("No graded rows found in the given files.")
        return

    def reliable(prompt_id: str, model: str) -> bool:
        passed, graded = counts[prompt_id][model]
        return graded > 0 and passed == graded

    labels = {}
    print(f"{'prompt':<28}{'local':>7}{'20b':>7}{'120b':>7}   tier")
    for prompt_id, by_model in counts.items():
        cells = [f"{by_model[m][0]}/{by_model[m][1]}" for m in MODELS]
        if reliable(prompt_id, "ollama-local"):
            tier = "simple"
        elif reliable(prompt_id, "groq-20b"):
            tier = "moderate"
        elif reliable(prompt_id, "groq-120b"):
            tier = "complex"
        else:
            tier = "UNSOLVED"
        print(f"{prompt_id:<28}{cells[0]:>7}{cells[1]:>7}{cells[2]:>7}   {tier}")
        if tier != "UNSOLVED":
            labels[prompt_id] = tier

    out_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")
    print(f"\nWrote {len(labels)} labels to {out_path}")


if __name__ == "__main__":
    main()