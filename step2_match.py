"""
Trump Stock Tracker — Step 2: the matching / filtering layer.

PROBLEM this solves: Step 1 pulls ~100 headlines, but most are noise
("stocks fall", "market crash", "buying Chagos Islands"). We only care
about headlines that look like Trump ENDORSING a specific company.

This file fetches the headlines (reusing Step 1) and then scores each one:
  - Does it name a company we're watching?  (required)
  - Does it use endorsement language ("go buy", "praised", "loves")?  (good)
  - Does it use negative language ("slams", "crash", "tariff")?       (bad)

It then sorts headlines into tiers so you can see signal vs. noise clearly.
Still no notifications yet — we earn trust in the filter first.
"""

import re    # 'regular expressions' — lets us match whole words precisely
import sys   # used below to fix how Windows' terminal prints special characters

# We reuse the fetching/parsing we already wrote and tested in Step 1.
# This is the payoff of keeping things modular: Step 2 doesn't re-solve
# a problem Step 1 already solved.
from step1_fetch_news import fetch_feed, parse_headlines, FEED_URL


# --- The watchlist ---------------------------------------------------------
# The companies we actually care about. Keyed by ticker (what you'd buy),
# with the name variations that might appear in a headline.
#
# WHY name-based and not ticker-based matching: headlines almost always say
# "Nvidia", rarely "NVDA". So names are the real signal; tickers are a bonus.
# Dell and Micron are here because they're your proven cases. Expand freely.
WATCHLIST = {
    "DELL": ["Dell", "Dell Technologies"],
    "MU":   ["Micron"],
    "NVDA": ["Nvidia"],
    "AAPL": ["Apple"],
    "TSLA": ["Tesla"],
    "AMD":  ["AMD", "Advanced Micro Devices"],
    "INTC": ["Intel"],
    "PLTR": ["Palantir"],
    "F":    ["Ford"],
    "GM":   ["General Motors"],
    "BA":   ["Boeing"],
    "X":    ["U.S. Steel", "US Steel", "United States Steel"],
}

# Words that suggest a genuine endorsement / positive mention.
# Each adds to a headline's score.
ENDORSEMENT_WORDS = [
    "go buy", "buy a", "should buy", "praised", "praises", "loves",
    "endorsed", "endorses", "touts", "touted", "backs", "backed",
    "great company", "favorite", "recommends", "bullish", "boosts",
    "go and buy",
]

# Words that suggest the headline is NOT a buy signal (attacks, bad news,
# policy fights). Each subtracts from the score.
NEGATIVE_WORDS = [
    "slams", "slammed", "attacks", "attacked", "criticizes", "criticized",
    "sues", "lawsuit", "crash", "crashes", "falls", "fall", "plunge",
    "plunges", "tumble", "tumbles", "tariff", "tariffs", "ban", "bans",
    "warns", "warning", "fraud", "probe", "investigation", "drops",
]


def find_companies(text):
    """Return the tickers of any watchlist companies named in the text."""
    found = []
    for ticker, names in WATCHLIST.items():
        for name in names:
            # \b means 'word boundary' so "Ford" won't match "Stafford",
            # and "AMD" won't match inside another word. re.IGNORECASE
            # makes it case-insensitive.
            pattern = r"\b" + re.escape(name) + r"\b"
            if re.search(pattern, text, re.IGNORECASE):
                found.append(ticker)
                break   # one name match is enough for this company
    return found


def count_hits(text, word_list):
    """Count how many words from word_list appear in the text."""
    text_low = text.lower()
    return sum(1 for w in word_list if w in text_low)


def score_headline(title):
    """
    Turn a headline into a result dict with companies + a signal score.
    Higher score = more likely a real endorsement of a watched company.
    """
    companies = find_companies(title)
    if not companies:
        return None   # not about any company we care about — ignore entirely

    endorsement_hits = count_hits(title, ENDORSEMENT_WORDS)
    negative_hits = count_hits(title, NEGATIVE_WORDS)

    # Simple, transparent scoring. We can tune these numbers later once we
    # see how it behaves on real headlines.
    score = (endorsement_hits * 2) - negative_hits

    if endorsement_hits >= 1 and negative_hits == 0:
        tier = "HIGH"      # looks like a clean endorsement
    elif endorsement_hits >= 1:
        tier = "REVIEW"    # endorsement words but also negatives — eyeball it
    else:
        tier = "LOW"       # names a company but no endorsement language

    return {
        "companies": companies,
        "score": score,
        "tier": tier,
        "endorsement_hits": endorsement_hits,
        "negative_hits": negative_hits,
    }


def deduplicate(headlines):
    """
    Remove duplicate stories. Google News titles look like
    "Real headline - Source". Many outlets cover the same event, so we
    strip the " - Source" suffix and drop titles we've already seen.
    """
    seen = set()
    unique = []
    for h in headlines:
        # Take everything before the last " - " (the outlet name).
        core = h["title"].rsplit(" - ", 1)[0].strip().lower()
        if core not in seen:
            seen.add(core)
            unique.append(h)
    return unique


def main():
    # The headlines contain "smart quotes" and long dashes (UTF-8). Windows'
    # default terminal can't print those and shows '�'. This line tells Python
    # to print in UTF-8 so the text displays correctly. (Display-only fix —
    # the data was always stored correctly.)
    sys.stdout.reconfigure(encoding="utf-8")

    print("Fetching live Trump news and scoring it...\n")
    raw = fetch_feed(FEED_URL)
    headlines = parse_headlines(raw)
    headlines = deduplicate(headlines)

    # Score each headline; keep only the ones that name a watched company.
    results = []
    for h in headlines:
        scored = score_headline(h["title"])
        if scored is not None:
            results.append({**h, **scored})

    # Sort so the strongest signals are at the top.
    tier_order = {"HIGH": 0, "REVIEW": 1, "LOW": 2}
    results.sort(key=lambda r: (tier_order[r["tier"]], -r["score"]))

    print(f"Scanned {len(headlines)} unique headlines.")
    print(f"Found {len(results)} that mention a watched company.\n" + "=" * 64)

    if not results:
        print("No watchlist companies mentioned right now. (Normal — "
              "Trump isn't endorsing a stock every hour.)")
        return

    for r in results:
        tickers = ", ".join(r["companies"])
        print(f"[{r['tier']}] {tickers}  (score {r['score']})")
        print(f"   {r['title']}")
        print(f"   {r['source']}  |  {r['pub_date']}\n")


if __name__ == "__main__":
    main()
