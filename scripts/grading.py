import json


def normalize(s: str) -> str:
    return s.lower().strip().lstrip("$").rstrip(".!?")


def grade(answer: str, item: dict) -> bool | None:
    """True/False for auto-gradable items, None for manual ones."""
    expected = item["expected"]
    check = item["check"]

    if check == "exact":
        return normalize(answer) == normalize(expected)

    if check == "contains":
        return normalize(expected) in normalize(answer)

    if check == "json":
        try:
            return json.loads(answer.strip()) == json.loads(expected)
        except json.JSONDecodeError:
            return False      

    if check == "manual":
        return None              

    raise ValueError(f"Unknown check type: {check!r}")