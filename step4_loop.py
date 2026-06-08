"""
Trump Stock Tracker — Step 4: the 24/7 loop.

Everything so far runs ONCE and stops. This file runs the check over and
over on a timer, so the program keeps watching the news on its own.

Design points that matter:
  - It calls run_check() from Step 3 — it doesn't re-implement anything.
  - One bad cycle (e.g. a brief internet drop) must NOT kill the loop. We
    catch errors, log them, and try again next time.
  - You stop it cleanly with Ctrl+C.

NOTE: this keeps running only while THIS program is open and your computer
is awake and online. Making it survive a closed laptop is the 'hosting'
step we'll do next.
"""

import sys
import time
from datetime import datetime

from step3_monitor import run_check


# How often to check the news, in seconds. 90s = every minute and a half.
# Why not faster: it's free RSS, and your own context notes the rallies last
# days — being 90s "late" costs nothing, and hammering the feed risks getting
# rate-limited (temporarily blocked) by Google.
CHECK_EVERY_SECONDS = 90


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 64)
    print("Trump Stock Tracker — LIVE")
    print(f"Checking every {CHECK_EVERY_SECONDS} seconds. Press Ctrl+C to stop.")
    print("=" * 64 + "\n")

    cycle = 0
    while True:
        cycle += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n----- Check #{cycle} at {now} -----")
        try:
            run_check()
        except Exception as e:
            # Catch ANYTHING (bad network, malformed feed, etc.) so the loop
            # survives. We just report it and wait for the next cycle.
            print(f"!! Check failed this cycle: {e}")
            print("   (Will try again next cycle — the loop keeps running.)")

        # Wait before the next check. Ctrl+C during the wait stops cleanly.
        try:
            time.sleep(CHECK_EVERY_SECONDS)
        except KeyboardInterrupt:
            print("\n\nStopped by you (Ctrl+C). Goodbye.")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by you (Ctrl+C). Goodbye.")
