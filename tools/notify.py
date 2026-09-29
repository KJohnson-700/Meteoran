"""Push a notification to the operator's phone via ntfy.sh. No account, no key.

The topic below is a private, unguessable channel. Anyone who knows the string can
post to it and read it, so it is derived from a local seed and never committed
anywhere public. Change TOPIC (and resubscribe on the phone) if it ever leaks.

Subscribe on the phone:  install "ntfy" (App Store / Play Store) -> + -> paste the topic
Or just open:            https://ntfy.sh/mtr-c62e338784373ff4  in the phone browser

    python3 tools/notify.py "title" "body" [priority]     # priority: min|low|default|high|urgent
"""
import json, sys, urllib.request

TOPIC = "mtr-c62e338784373ff4"
URL = f"https://ntfy.sh/{TOPIC}"


def screen(title, body, urgent=False):
    """macOS notification -- pops on THIS screen, no browser needed. Never raises."""
    import subprocess
    try:
        esc = lambda t: t.replace("\\", "").replace('"', "'").replace("\n", " ")
        sound = "Sosumi" if urgent else "Ping"
        subprocess.run(["osascript", "-e",
            f'display notification "{esc(body)[:220]}" with title "{esc(title)[:60]}" sound name "{sound}"'],
            capture_output=True, timeout=10)
        return True
    except Exception:
        return False


def push(title, body, priority="default", tags=""):
    """-> True if the phone push was accepted. Never raises; alerting must not crash a poller.
    Also fires a macOS notification so it lands on screen as well as on the phone."""
    screen(title, body, urgent=(priority == "urgent"))
    try:
        req = urllib.request.Request(
            URL, data=body.encode("utf-8"), method="POST",
            headers={"Title": title, "Priority": priority, "Tags": tags or "chart_with_upwards_trend"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status < 300
    except Exception as e:
        print(f"  [notify failed: {e}]")
        return False


if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "Meteoran"
    b = sys.argv[2] if len(sys.argv) > 2 else "test"
    p = sys.argv[3] if len(sys.argv) > 3 else "default"
    print("sent" if push(t, b, p) else "FAILED", "->", URL)
