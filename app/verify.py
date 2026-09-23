"""Cheap, deterministic answer checks. Free and instant — run before any LLM judge."""

import json
import re

REFUSAL_PATTERNS = (
    r"\bi can'?t\b",
    r"\bi cannot\b",
    r"\bi'?m (?:not able|unable)\b",
    r"\bi won'?t\b",
    r"\bas an ai\b",
)
BARE_NUMBER = re.compile(r"^-?\$?-?\d[\d,]*(?:\.\d+)?%?$")


JUDGE_PROMPT = """You are grading an AI assistant's answer.

Question:
{prompt}

Answer:
{answer}

Is the answer correct and does it follow the question's instructions?
Reply with exactly one word: CORRECT or INCORRECT."""


async def judge(prompt: str, answer: str, provider, config,
                fail_open: bool = False) -> tuple[bool, str]:
    """LLM-as-judge check. Returns (ok, reason). Costs one call on `config`."""
    for attempt in (1, 2):
        response = await provider.send(
            JUDGE_PROMPT.format(prompt=prompt, answer=answer), config
        )
        verdict = response.text.strip().upper()
        if verdict.startswith("CORRECT"):
            return True, "judge: correct"
        if verdict.startswith("INCORRECT"):
            return False, "judge: incorrect"
    return fail_open, f"judge: no clear verdict after 2 tries, fail_{'open' if fail_open else 'closed'}"

def verify(prompt: str, answer: str) -> tuple[bool, str]:
    """Return (ok, reason). ok=False means: escalate to a stronger model."""
    a = answer.strip()
    if not a:
        return False, "empty answer"

    low = a.lower()
    if any(re.search(p, low) for p in REFUSAL_PATTERNS):
        return False, "refusal"

    p = prompt.lower()
    core = a.rstrip(".!").strip().strip('"').strip("'")

    if "json" in p and ("json only" in p or "valid json" in p):
        try:
            json.loads(a)
        except json.JSONDecodeError:
            return False, "expected valid JSON"

    if "only the number" in p or "just the number" in p:
        if not BARE_NUMBER.match(core.replace(" ", "")):
            return False, "expected a bare number"

    if "one word" in p and len(core.split()) != 1:
        return False, "expected one word"

    if "reply yes or no" in p and core.lower() not in ("yes", "no"):
        return False, "expected yes or no"

    if ("only the name" in p or "only the letter" in p) and len(core.split()) > 2:
        return False, "expected only a name/letter"

    return True, "passed checks"