"""Minimal HTML dashboard rendered from stats. No framework, no build step."""


def render(stats: dict, app_name: str, version: str) -> str:
    """Return a self-contained HTML page showing routing savings."""
    daily = stats.get("daily", [])
    max_cost = max((max(d["baseline"], d["cost"]) for d in daily), default=0) or 1

    bars = ""
    for d in daily:
        base_h = max(int(d["baseline"] / max_cost * 90), 2)
        cost_h = max(int(d["cost"] / max_cost * 90), 2)
        bars += (
            '<div class="day">'
            '<div class="bars">'
            f'<div class="bar base" style="height:{base_h}px" '
            f'title="baseline ${d["baseline"]:.6f}"></div>'
            f'<div class="bar act" style="height:{cost_h}px" '
            f'title="actual ${d["cost"]:.6f}"></div>'
            "</div>"
            f'<div class="lbl">{d["day"][5:]}</div>'
            "</div>"
        )
    if not bars:
        bars = '<div class="lbl">No data yet</div>'

    rows = "".join(
        f"<tr><td>{m['model']}</td><td>{m['requests']}</td>"
        f"<td>${m['cost']:.6f}</td><td>{int(m['avg_latency_ms'])} ms</td></tr>"
        for m in stats.get("by_model", [])
    ) or "<tr><td colspan='4'>No requests yet</td></tr>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{app_name} - stats</title>
<style>
body {{ font: 14px/1.5 system-ui, sans-serif; margin: 0; background: #121417; color: #e8e4de; }}
.wrap {{ max-width: 760px; margin: 0 auto; padding: 40px 24px; }}
h1 {{ font-size: 20px; margin: 0 0 4px; }}
.sub {{ color: #8d8880; font-size: 13px; margin-bottom: 28px; }}
.hero {{ background: #1b1e22; border-radius: 10px; padding: 24px; margin-bottom: 20px; }}
.big {{ font-size: 44px; font-weight: 700; color: #c1703a; line-height: 1; }}
.cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }}
.card {{ flex: 1; min-width: 150px; background: #1b1e22; border-radius: 10px; padding: 16px; }}
.card .v {{ font-size: 22px; font-weight: 600; }}
.card .k {{ color: #8d8880; font-size: 12px; }}
table {{ width: 100%; border-collapse: collapse; background: #1b1e22; border-radius: 10px; overflow: hidden; }}
th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #2a2e33; font-size: 13px; }}
th {{ color: #8d8880; font-weight: 500; font-size: 11px; text-transform: uppercase; }}
.chart {{ display: flex; gap: 10px; align-items: flex-end; height: 120px; margin: 16px 0 4px; }}
.day {{ text-align: center; }}
.bars {{ display: flex; gap: 3px; align-items: flex-end; height: 95px; }}
.bar {{ width: 14px; border-radius: 2px 2px 0 0; }}
.base {{ background: #3a4048; }}
.act {{ background: #c1703a; }}
.lbl {{ font-size: 10px; color: #8d8880; margin-top: 6px; }}
.legend {{ font-size: 11px; color: #8d8880; }}
.sw {{ display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin: 0 4px 0 12px; }}
h3 {{ font-size: 13px; color: #8d8880; text-transform: uppercase; margin: 28px 0 10px; }}
</style></head><body><div class="wrap">

<h1>{app_name}</h1>
<div class="sub">v{version} &middot; last {stats.get('window_days', 7)} days</div>

<div class="hero">
  <div class="big">{stats.get('savings_pct', 0)}%</div>
  <div class="sub" style="margin:6px 0 0">
    cheaper than routing everything to the cloud model
    (${stats.get('saved_usd', 0):.6f} saved on {stats.get('requests', 0)} requests)
  </div>
</div>

<div class="cards">
  <div class="card"><div class="v">{stats.get('requests', 0)}</div><div class="k">requests</div></div>
  <div class="card"><div class="v">${stats.get('cost_usd', 0):.6f}</div><div class="k">actual cost</div></div>
  <div class="card"><div class="v">${stats.get('baseline_cost_usd', 0):.6f}</div><div class="k">baseline cost</div></div>
  <div class="card"><div class="v">{stats.get('avg_latency_ms', 0)} ms</div><div class="k">avg latency</div></div>
</div>

<div class="chart">{bars}</div>
<div class="legend"><span class="sw base"></span>baseline<span class="sw act"></span>actual</div>

<h3>By model</h3>
<table>
<tr><th>Model</th><th>Requests</th><th>Cost</th><th>Avg latency</th></tr>
{rows}
</table>

</div></body></html>"""