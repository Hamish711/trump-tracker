"""
Trump Stock Tracker — Step 3: recency + memory (the "only tell me what's NEW" layer).

Step 2 found relevant headlines but had two problems for automation:
  1. It surfaced OLD stories ("Dell up 255%") that aren't fresh signals.
  2. Run it twice and it shows the same headlines again — it has no memory.

This file fixes both:
  - RECENCY: ignore anything older than MAX_AGE_HOURS, using each headline's
    publish time.
  - MEMORY: remember every headline we've already reported (saved to a file
    on disk), so the same story never alerts you twice — even after you close
    and reopen the program.

This is the piece that makes notifications + a 24/7 loop sane instead of spammy.
"""

import sys
import json                         # to save/load our memory file
import hashlib                      # to make a short, stable ID for each story
from pathlib import Path           # clean way to handle file paths
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime   # parses RSS date strings

# Reuse everything we already built and tested.
from step1_fetch_news import fetch_feed, parse_headlines, FEED_URL
from step2_match import score_headline, deduplicate
from notify import send_push


# --- Settings you can tune -------------------------------------------------
MAX_AGE_HOURS = 72   # ignore headlines older than this. Tighten to ~6 for
                     # real monitoring; 72 here so we can see results in a demo.

# Where we store our memory of already-seen stories. It lives next to this
# script, so it works no matter what folder you run the program from.
STATE_FILE = Path(__file__).parent / "seen.json"

# How long to remember a story before forgetting it (keeps the file small).
FORGET_AFTER_DAYS = 30

# Which tiers actually buzz your phone. LOW headlines still print to screen
# but stay silent, so the app never becomes noise you learn to ignore.
NOTIFY_TIERS = {"HIGH", "REVIEW"}

# How loud each tier's notification is on your phone.
TIER_PRIORITY = {"HIGH": "max", "REVIEW": "high"}


# --- Memory (state) helpers ------------------------------------------------
def make_id(title):
    """
    Turn a headline into a short, stable fingerprint.

    WHY a hash: we strip the "- Source" suffix so the same story from
    different outlets shares one ID, then hash it to a tidy string. Same
    story -> same ID every time, which is exactly what 'have I seen this?'
    needs.
    """
    core = title.rsplit(" - ", 1)[0].strip().lower()
    return hashlib.sha1(core.encode("utf-8")).hexdigest()[:16]


def load_seen():
    """Load our memory file, or start empty if it doesn't exist yet."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}   # {story_id: {"title": ..., "first_seen": ISO-timestamp}}


def save_seen(seen):
    """Write memory back to disk, after forgetting very old entries."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=FORGET_AFTER_DAYS)
    pruned = {}
    for story_id, info in seen.items():
        first_seen = datetime.fromisoformat(info["first_seen"])
        if first_seen >= cutoff:
            pruned[story_id] = info
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(pruned, f, indent=2)


# --- Recency helper --------------------------------------------------------
def is_recent(pub_date_str):
    """True if the headline was published within MAX_AGE_HOURS."""
    if not pub_date_str:
        return False   # no date -> can't trust it's fresh, so skip
    try:
        published = parsedate_to_datetime(pub_date_str)
    except (TypeError, ValueError):
        return False
    age = datetime.now(timezone.utc) - published
    return age <= timedelta(hours=MAX_AGE_HOURS)


# --- Main flow -------------------------------------------------------------
def run_check():
    """
    Do ONE full news check: fetch, filter, remember, notify.
    Returns the list of new alerts (so a loop can act on / count them).
    This is the reusable 'one heartbeat' the loop will call repeatedly.
    """
    seen = load_seen()
    print(f"Loaded memory of {len(seen)} previously-seen stories.")
    print("Fetching live Trump news...\n")

    raw = fetch_feed(FEED_URL)
    headlines = deduplicate(parse_headlines(raw))

    new_alerts = []
    for h in headlines:
        # 1) Must be about a watched company with a signal score.
        scored = score_headline(h["title"])
        if scored is None:
            continue
        # 2) Must be recent.
        if not is_recent(h["pub_date"]):
            continue
        # 3) Must be something we haven't already reported.
        story_id = make_id(h["title"])
        if story_id in seen:
            continue

        # It's a genuinely new, recent, relevant headline.
        new_alerts.append({**h, **scored, "id": story_id})
        # Record it so we never alert on it again.
        seen[story_id] = {
            "title": h["title"],
            "first_seen": datetime.now(timezone.utc).isoformat(),
        }

    save_seen(seen)

    # Sort strongest signals first.
    tier_order = {"HIGH": 0, "REVIEW": 1, "LOW": 2}
    new_alerts.sort(key=lambda r: (tier_order[r["tier"]], -r["score"]))

    print("=" * 64)
    if not new_alerts:
        print("No NEW relevant headlines since last check. (This is the "
              "normal, quiet state most of the time.)")
        return new_alerts

    print(f"{len(new_alerts)} NEW headline(s) worth your attention:\n")
    for r in new_alerts:
        tickers = ", ".join(r["companies"])
        print(f"[{r['tier']}] {tickers}  (score {r['score']})")
        print(f"   {r['title']}")
        print(f"   {r['source']}  |  {r['pub_date']}")
        print(f"   {r['link']}\n")

        # Push to the phone only for the tiers we decided are worth a buzz.
        if r["tier"] in NOTIFY_TIERS:
            try:
                send_push(
                    message=f"{r['title']}\n\nSource: {r['source']}",
                    title=f"[{r['tier']}] Trump → {tickers}",
                    priority=TIER_PRIORITY[r["tier"]],
                    click_url=r["link"],
                )
                print("   ↳ phone notification sent.\n")
            except Exception as e:
                # A failed push must never crash the monitor — we just note it
                # and keep going. (e.g. brief loss of internet.)
                print(f"   ↳ notification failed: {e}\n")

    return new_alerts


def main():
    """Run a single check (used when you run this file directly)."""
    sys.stdout.reconfigure(encoding="utf-8")
    run_check()


if __name__ == "__main__":
    main()
