"""Template for tools/notify.py, which is gitignored because it holds a private topic.

ntfy.sh needs no account: pick an unguessable topic, subscribe to it in the ntfy app
on your phone, and POST to it. Anyone who knows the string can read AND post, so treat
it like a password and never commit it.

    cp tools/notify.example.py tools/notify.py    # then set TOPIC
"""
import sys, urllib.request

TOPIC = "CHANGE-ME-to-something-unguessable"
URL = f"https://ntfy.sh/{TOPIC}"


def screen(title, body, urgent=False):
    """macOS on-screen notification. Never raises -- alerting must not crash a poller."""
    import subprocess
    try:
        esc = lambda t: t.replace("\\", "").replace('"', "'").replace("\n", " ")
        subprocess.run(["osascript", "-e",
            f'display notification "{esc(body)[:220]}" with title "{esc(title)[:60]}" '
            f'sound name "{"Sosumi" if urgent else "Ping"}"'], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


def push(title, body, priority="default", tags=""):
    """-> True if the phone push was accepted. Also fires an on-screen notification."""
    screen(title, body, urgent=(priority == "urgent"))
    try:
        req = urllib.request.Request(URL, data=body.encode("utf-8"), method="POST",
            headers={"Title": title, "Priority": priority,
                     "Tags": tags or "chart_with_upwards_trend"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status < 300
    except Exception as e:
        print(f"  [notify failed: {e}]")
        return False


if __name__ == "__main__":
    a = sys.argv
    print("sent" if push(a[1] if len(a) > 1 else "Meteoran",
                         a[2] if len(a) > 2 else "test",
                         a[3] if len(a) > 3 else "default") else "FAILED", "->", URL)
