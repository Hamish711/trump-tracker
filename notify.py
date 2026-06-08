"""
Trump Stock Tracker — notification sender (ntfy.sh).

Sends a push to your phone via ntfy.sh. You POST a message to a URL ending
in your secret topic name; ntfy delivers it to every subscribed phone.

WHERE THE TOPIC COMES FROM (important for going public on GitHub):
We do NOT hard-code the topic anymore. If the code is in a public repo,
a hard-coded topic would let strangers spam your phone. Instead we read it
from:
  1) the NTFY_TOPIC environment variable  (used by GitHub Actions, via a
     private "Secret"), or
  2) a local file 'ntfy_topic.txt'        (used on your own computer; this
     file is git-ignored so it never gets uploaded).
"""

import os
import urllib.request
from pathlib import Path


def _load_topic():
    """Find the ntfy topic from the environment or a local file."""
    # 1) Environment variable — this is how GitHub Actions will pass it,
    #    securely, from a repository Secret.
    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        return topic.strip()

    # 2) Local file fallback for running on your own machine.
    local_file = Path(__file__).parent / "ntfy_topic.txt"
    if local_file.exists():
        return local_file.read_text(encoding="utf-8").strip()

    raise RuntimeError(
        "No ntfy topic found. Set the NTFY_TOPIC environment variable, "
        "or create a file called ntfy_topic.txt next to notify.py."
    )


def send_push(message, title="Trump Stock Tracker", priority="default",
              click_url=None):
    """
    Send a notification to your phone.

    message   : the body text of the notification
    title     : the bold title line
    priority  : "default", "high", or "max"
    click_url : optional link opened when you tap the notification
    """
    topic = _load_topic()
    url = "https://ntfy.sh/" + topic

    # ntfy reads title/priority/etc. from HTTP headers, which must be plain
    # ASCII, so we strip fancy characters out of the title to avoid errors.
    headers = {
        "Title": title.encode("ascii", "ignore").decode(),
        "Priority": priority,
    }
    if click_url:
        headers["Click"] = click_url

    data = message.encode("utf-8")   # the body CAN be full UTF-8
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status


if __name__ == "__main__":
    status = send_push(
        "If you can read this on your phone, notifications work. 🎉",
        title="Test — Trump Tracker",
        priority="high",
    )
    print(f"Sent test notification. Server responded with status {status}.")
