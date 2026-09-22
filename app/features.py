"""Turn a prompt into numeric features for the tier classifier."""

import re

CALC_WORDS = ("total", "after", "days", "percent", "discount", "tax", "change",
              "cost", "price", "rounded", "sum", "how much", "how many")
MONTHS = ("january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december")


def extract_features(prompt: str) -> dict[str, float]:
    text = prompt.lower()
    return {
        "n_chars": len(prompt),
        "n_lines": prompt.count("\n") + 1,
        "n_numbers": len(re.findall(r"\d+(?:\.\d+)?", prompt)),
        "n_sentences": len(re.findall(r"[.!?](?:\s|$)", prompt)),
        "n_comparisons": len(re.findall(r"\b(?:older|younger|before|after|taller|shorter) than\b", text)),
        "has_calc_word": float(any(w in text for w in CALC_WORDS)),
        "has_currency": float("$" in prompt),
        "has_percent": float("%" in prompt),
        "has_month": float(any(m in text for m in MONTHS)),
        "has_letter_count": float("how many times" in text or "letter" in text),
        "has_code": float("def " in prompt or "```" in prompt),
        "has_sentiment": float(any(w in text for w in ("review", "sentiment", "mixed"))),
        "asks_json": float("json" in text),
        "asks_only_answer": float("reply with only" in text or "reply with just" in text),
    }