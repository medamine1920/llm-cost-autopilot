"""Generate synthetic golden items with Python-computed answers.

Run: python -m scripts.generate_prompts
Writes data/golden_v3.json = golden_v2 + generated items (tier_label "tbd").
"""

import json
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

random.seed(7)  # reproducible dataset

NAMES = ["Anna", "Ben", "Carl", "Dana", "Eli", "Fay", "Gus", "Hana"]
WORDS = ["banana", "committee", "mississippi", "bookkeeper", "parallel",
         "occurrence", "strawberry", "assessment", "raspberry", "balloon"]
PHRASES = ["the quick brown fox", "hello world from tunis", "data beats opinions",
           "ship it on friday", "keep calm and deploy", "cheap models first"]
ORDINALS = ["oldest", "second-oldest", "third-oldest",
            "fourth-oldest", "fifth-oldest", "sixth-oldest"]


def money(x: float) -> str:
    return str(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def item(id_: str, text: str, expected, check: str = "exact") -> dict:
    return {"id": id_, "text": text, "tier_label": "tbd",
            "expected": str(expected), "check": check}


# ---------- families ----------

def gen_add(i):
    a, b = random.randint(10, 99), random.randint(10, 99)
    return item(f"add_{i}", f"What is {a} + {b}? Reply with only the number.", a + b)


def gen_upper(i):
    p = random.choice(PHRASES)
    return item(f"upper_{i}", f"Convert to uppercase: {p}", p.upper())


def gen_extract(i):
    name = random.choice(NAMES)
    email = f"{name.lower()}{random.randint(1, 99)}@{random.choice(['acme.com', 'shop.io', 'mail.net'])}"
    return item(f"extract_{i}",
                f"Extract the email from: 'Please reach {name} at {email} before Friday.' Reply with only the email.",
                email)


def gen_json(i):
    name, age = random.choice(NAMES), random.randint(18, 80)
    city = random.choice(["Paris", "Tunis", "Berlin", "Madrid"])
    return item(f"json_{i}",
                f"Reply with valid JSON only, no other text, with keys name, age and city: "
                f"'{name} is {age} years old and lives in {city}.'",
                json.dumps({"name": name, "age": age, "city": city}), "json")


def gen_letters_easy(i):
    w = random.choice(WORDS)
    letter = random.choice(sorted(set(w)))
    return item(f"letters1_{i}",
                f"How many times does the letter {letter} appear in '{w}'? Reply with only the number.",
                w.count(letter))


def gen_letters_hard(i):
    phrase = " ".join(random.sample(WORDS, 2))
    letter = random.choice(sorted(set(phrase.replace(" ", ""))))
    return item(f"letters2_{i}",
                f"How many times does the letter {letter} appear in '{phrase}'? Reply with only the number.",
                phrase.count(letter))


def gen_date(i):
    start = date(2026, 1, 1) + timedelta(days=random.randint(0, 300))
    n = random.randint(5, 60)
    end = start + timedelta(days=n)
    return item(f"date_{i}",
                f"What date is {n} days after {start:%B} {start.day}? "
                f"Reply with only the month and day, like 'June 3'.",
                f"{end:%B} {end.day}".lower())


def gen_discount(i):
    price = random.choice([40, 60, 80, 120, 150])
    d1, d2, tax = random.choice([10, 20, 25, 30]), random.choice([5, 10, 15]), random.choice([5, 8, 10])
    final = price * (1 - d1 / 100) * (1 - d2 / 100) * (1 + tax / 100)
    return item(f"discount_{i}",
                f"An item costs ${price}. It gets {d1}% off, then an extra {d2}% off the discounted price, "
                f"then {tax}% tax is added. What is the final price? Reply with only the number rounded to 2 decimals.",
                money(final))


def gen_invoice(i, n):
    rows = [(f"Item {k + 1}", round(random.uniform(5, 150), 2)) for k in range(n)]
    total = sum(p for _, p in rows if p > 50)
    lines = "\n".join(f"{name} - ${p:.2f}" for name, p in rows)
    return item(f"invoice{n}_{i}",
                f"Invoice:\n{lines}\n\nWhat is the total of only the items priced over $50? "
                f"Reply with just the number rounded to 2 decimals.",
                money(total))


def gen_order(i, n):
    people = random.sample(NAMES, n)              # index 0 = oldest
    clues = [f"{people[k]} is older than {people[k + 1]}." for k in range(n - 1)]
    random.shuffle(clues)
    k = random.randint(0, n - 1)
    return item(f"order{n}_{i}",
                f"{' '.join(clues)} Who is the {ORDINALS[k]}? Reply with only the name.",
                people[k].lower())


PLAN = [
    (gen_add, 8), (gen_upper, 8), (gen_extract, 8), (gen_json, 8),
    (gen_letters_easy, 8), (gen_letters_hard, 8),
    (gen_date, 12), (gen_discount, 12),
    (lambda i: gen_invoice(i, 3), 8), (lambda i: gen_invoice(i, 10), 10),
    (lambda i: gen_order(i, 3), 8), (lambda i: gen_order(i, 6), 10),
]


def main() -> None:
    base = json.loads(Path("data/golden_v2.json").read_text(encoding="utf-8"))
    generated = [fn(i) for fn, count in PLAN for i in range(count)]

    ids = [x["id"] for x in base + generated]
    assert len(ids) == len(set(ids)), "duplicate ids!"

    out = Path("data/golden_v3.json")
    out.write_text(json.dumps(base + generated, indent=2), encoding="utf-8")
    print(f"Wrote {len(base) + len(generated)} items to {out} ({len(generated)} generated)")


if __name__ == "__main__":
    main()