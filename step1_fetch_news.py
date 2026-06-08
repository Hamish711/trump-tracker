"""
Trump Stock Tracker — Step 1, v1: prove we can pull live news.

Goal of THIS file: fetch real, current news headlines about Trump from
Google News, and print them. That's it. No matching, no notifications yet.
If this runs and shows recent headlines, the hardest external dependency
(getting live data for free) is proven to work.

Uses only Python's built-in tools so there's nothing to install yet.
"""

import urllib.request          # fetches a web page / feed over the internet
import urllib.parse            # safely encodes our search query into the URL
import xml.etree.ElementTree as ET   # reads the XML format that RSS feeds use


# --- The data source -------------------------------------------------------
# Google News exposes a free RSS feed for any search query. No API key, no
# signup. We ask it for news matching our query. The query below looks for
# "Trump" together with stock-related words to cut down obvious junk.
QUERY = 'Trump (stock OR shares OR "buy")'

# Google News RSS search URL. The %-codes are just the query, URL-encoded.
# hl/gl/ceid tell Google we want US English results.
FEED_URL = (
    "https://news.google.com/rss/search?"
    "q=" + urllib.parse.quote(QUERY) +
    "&hl=en-US&gl=US&ceid=US:en"
)


def fetch_feed(url):
    """Download the raw RSS feed text from the given URL."""
    # We send a fake "browser" User-Agent header. Why: some servers ignore or
    # block requests that don't look like a real browser. This is a harmless,
    # standard practice for reading public feeds.
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def parse_headlines(raw_xml):
    """Pull the headline, link, source, and time out of the feed."""
    root = ET.fromstring(raw_xml)
    # In RSS, each article is an <item>. We dig into channel > item.
    items = root.findall("./channel/item")

    headlines = []
    for item in items:
        title = item.findtext("title", default="(no title)")
        link = item.findtext("link", default="")
        pub_date = item.findtext("pubDate", default="")
        # Google nests the outlet name inside a <source> tag.
        source_el = item.find("source")
        source = source_el.text if source_el is not None else "(unknown source)"
        headlines.append({
            "title": title,
            "link": link,
            "source": source,
            "pub_date": pub_date,
        })
    return headlines


def main():
    print("Fetching live Trump news from Google News...\n")
    raw = fetch_feed(FEED_URL)
    headlines = parse_headlines(raw)

    print(f"Got {len(headlines)} headlines.\n" + "-" * 60)
    for i, h in enumerate(headlines, start=1):
        print(f"{i:>2}. {h['title']}")
        print(f"    source: {h['source']}  |  {h['pub_date']}")
        print(f"    {h['link']}\n")


if __name__ == "__main__":
    main()
