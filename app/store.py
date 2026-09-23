"""Persistent request log (SQLite)."""

import hashlib
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    prompt_chars INTEGER NOT NULL,
    tier TEXT NOT NULL,
    model TEXT NOT NULL,
    routing_reason TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    baseline_cost_usd REAL NOT NULL,
    latency_ms INTEGER NOT NULL,
    escalated INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_requests_ts ON requests(ts);
"""


class RequestStore:
    """Append-only log of routed requests, used for budget and stats."""

    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def record(self, prompt: str, tier: str, model: str, routing_reason: str,
               input_tokens: int, output_tokens: int, cost_usd: float,
               baseline_cost_usd: float, latency_ms: int,
               escalated: bool = False) -> None:
        """Log one request. Never raises: logging must not break serving."""
        try:
            self.conn.execute(
                """INSERT INTO requests
                   (ts, prompt_hash, prompt_chars, tier, model, routing_reason,
                    input_tokens, output_tokens, cost_usd, baseline_cost_usd,
                    latency_ms, escalated)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    len(prompt),
                    tier,
                    model,
                    routing_reason,
                    input_tokens,
                    output_tokens,
                    cost_usd,
                    baseline_cost_usd,
                    latency_ms,
                    int(escalated),
                ),
            )
            self.conn.commit()
        except sqlite3.Error:
            logger.exception("failed to record request")

    def spent_today(self) -> float:
        today = datetime.now(timezone.utc).date().isoformat()
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0.0) AS total FROM requests WHERE ts >= ?",
            (today,),
        ).fetchone()
        return float(row["total"])

    def stats(self, days: int = 7) -> dict:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        totals = self.conn.execute(
            """SELECT COUNT(*) AS requests,
                      COALESCE(SUM(cost_usd), 0.0) AS cost,
                      COALESCE(SUM(baseline_cost_usd), 0.0) AS baseline,
                      COALESCE(SUM(escalated), 0) AS escalations,
                      COALESCE(AVG(latency_ms), 0) AS avg_latency_ms
               FROM requests WHERE ts >= ?""",
            (since,),
        ).fetchone()

        by_model = self.conn.execute(
            """SELECT model,
                      COUNT(*) AS requests,
                      COALESCE(SUM(cost_usd), 0.0) AS cost,
                      COALESCE(AVG(latency_ms), 0) AS avg_latency_ms
               FROM requests WHERE ts >= ?
               GROUP BY model ORDER BY requests DESC""",
            (since,),
        ).fetchall()

        daily = self.conn.execute(
            """SELECT substr(ts, 1, 10) AS day,
                      COUNT(*) AS requests,
                      COALESCE(SUM(cost_usd), 0.0) AS cost,
                      COALESCE(SUM(baseline_cost_usd), 0.0) AS baseline
               FROM requests WHERE ts >= ?
               GROUP BY day ORDER BY day""",
            (since,),
        ).fetchall()

        cost = float(totals["cost"])
        baseline = float(totals["baseline"])
        savings_pct = (1 - cost / baseline) * 100 if baseline else 0.0

        return {
            "window_days": days,
            "requests": totals["requests"],
            "cost_usd": round(cost, 6),
            "baseline_cost_usd": round(baseline, 6),
            "saved_usd": round(baseline - cost, 6),
            "savings_pct": round(savings_pct, 1),
            "escalations": totals["escalations"],
            "avg_latency_ms": int(totals["avg_latency_ms"]),
            "by_model": [dict(r) for r in by_model],
            "daily": [dict(r) for r in daily],
        }