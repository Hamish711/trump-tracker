"""
Trump Stock Tracker — rough dashboard.

Builds a single HTML page showing the current Trump-stock headlines, scored
and colour-coded by tier, then opens it in your browser. Unlike the monitor,
this shows EVERYTHING relevant (not just new items) — it's for viewing, not
alerting. No web server, no extra libraries; just generates a file and opens it.

Run it any time you want a fresh look:  python dashboard.py
"""

import sys
import html
import webbrowser
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# Reuse the pieces we already built and tested.
from step1_fetch_news import fetch_feed, parse_headlines, FEED_URL
from step2_match import score_headline, deduplicate

OUTPUT_FILE = Path(__file__).parent / "dashboard.html"

# Colours for each tier (background, text).
TIER_STYLE = {
    "HIGH":   ("#1f7a3d", "#ffffff"),   # green  = clean endorsement
    "REVIEW": ("#b5860a", "#ffffff"),   # amber  = endorsement + noise
    "LOW":    ("#3a3f4b", "#cfd3dc"),   # grey   = just a mention
}


def parse_when(pub_date_str):
    """Return a datetime for sorting, or a very old date if unparseable."""
    try:
        return parsedate_to_datetime(pub_date_str)
    except (TypeError, ValueError):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def human_age(dt):
    """Turn a datetime into a friendly 'about 3 hours ago' style string."""
    delta = datetime.now(timezone.utc) - dt
    secs = delta.total_seconds()
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} hr ago"
    return f"{int(secs // 86400)} days ago"


def build_card(item):
    """Build one HTML card for a scored headline."""
    bg, fg = TIER_STYLE[item["tier"]]
    tickers = ", ".join(item["companies"])
    when = parse_when(item["pub_date"])
    # html.escape stops weird characters in titles from breaking the page.
    title = html.escape(item["title"])
    source = html.escape(item["source"])
    link = html.escape(item["link"])
    return f"""
    <a class="card" href="{link}" target="_blank" rel="noopener">
      <div class="badge" style="background:{bg};color:{fg};">
        {item['tier']} · {html.escape(tickers)} · score {item['score']}
      </div>
      <div class="title">{title}</div>
      <div class="meta">{source} &nbsp;•&nbsp; {human_age(when)}</div>
    </a>"""


def build_html(items, total_scanned):
    """Assemble the full HTML page from the scored items."""
    now = datetime.now().strftime("%A %d %b %Y, %H:%M")
    counts = {t: sum(1 for i in items if i["tier"] == t)
              for t in ("HIGH", "REVIEW", "LOW")}
    cards = "\n".join(build_card(i) for i in items) or \
        "<p style='color:#888'>No watchlist companies in the news right now.</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trump Stock Tracker</title>
<style>
  body {{ font-family: system-ui, sans-serif; background:#15171c; color:#e6e8ec;
         margin:0; padding:24px; }}
  h1 {{ margin:0 0 4px; font-size:22px; }}
  .sub {{ color:#8b909a; font-size:13px; margin-bottom:20px; }}
  .summary {{ display:flex; gap:10px; margin-bottom:20px; flex-wrap:wrap; }}
  .pill {{ padding:6px 12px; border-radius:20px; font-size:13px; font-weight:600; }}
  .card {{ display:block; text-decoration:none; color:inherit;
          background:#1d2026; border:1px solid #2a2e37; border-radius:10px;
          padding:14px 16px; margin-bottom:12px; transition:border-color .15s; }}
  .card:hover {{ border-color:#4a90d9; }}
  .badge {{ display:inline-block; padding:3px 9px; border-radius:6px;
            font-size:12px; font-weight:700; margin-bottom:8px; }}
  .title {{ font-size:16px; line-height:1.4; margin-bottom:6px; }}
  .meta {{ color:#8b909a; font-size:12px; }}
</style>
</head>
<body>
  <h1>🇺🇸 Trump Stock Tracker</h1>
  <div class="sub">Generated {now} &nbsp;•&nbsp; scanned {total_scanned} headlines &nbsp;•&nbsp; {len(items)} mention a watched company</div>
  <div class="summary">
    <span class="pill" style="background:#1f7a3d">HIGH: {counts['HIGH']}</span>
    <span class="pill" style="background:#b5860a">REVIEW: {counts['REVIEW']}</span>
    <span class="pill" style="background:#3a3f4b">LOW: {counts['LOW']}</span>
  </div>
  {cards}
</body>
</html>"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("Fetching live news and building dashboard...")

    raw = fetch_feed(FEED_URL)
    headlines = deduplicate(parse_headlines(raw))

    items = []
    for h in headlines:
        scored = score_headline(h["title"])
        if scored is not None:
            items.append({**h, **scored})

    # Sort: HIGH first, then REVIEW, then LOW; newest first within each tier.
    tier_order = {"HIGH": 0, "REVIEW": 1, "LOW": 2}
    items.sort(key=lambda i: (tier_order[i["tier"]], -parse_when(i["pub_date"]).timestamp()))

    OUTPUT_FILE.write_text(build_html(items, len(headlines)), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")
    webbrowser.open(OUTPUT_FILE.as_uri())   # open it in your default browser


if __name__ == "__main__":
    main()
