import pytest

from app.router import choose_tier


@pytest.mark.parametrize("prompt, expected_tier", [
    ("What is the capital of Japan? One word.", "simple"),
    ("Convert to uppercase: the quick brown fox", "simple"),
    ("Extract the email from: 'Contact John at john@acme.com'", "simple"),
    ("How many times does the letter r appear in 'strawberry'?", "moderate"),
    ("A car uses 6.5 liters per 100 km. What does 340 km cost at $1.80?", "moderate"),
    ("Anna is older than Ben. Ben is older than Carl. Carl is older than Dana. Who is youngest?", "moderate"),
    ("Is this review positive, negative, or mixed? 'Great battery, terrible camera.'", "moderate"),
])
def test_choose_tier(prompt, expected_tier):
    tier, reason = choose_tier(prompt)
    assert tier == expected_tier, reason