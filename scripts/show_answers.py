import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
results = json.loads(path.read_text(encoding="utf-8"))

for prompt_id in dict.fromkeys(r["prompt_id"] for r in results):
    print(f"\n===== {prompt_id} =====")
    for r in results:
        if r["prompt_id"] == prompt_id:
            answer = r.get("text", r.get("error", "")).strip().replace("\n", " ")
            print(f"  [{r['model']}] {answer[-250:]}")