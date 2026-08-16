"""
Tiny web server used only to keep free-tier hosts (like Replit) from
treating the process as idle/dead when running in polling mode. Some hosts
expect something bound to a port and/or want an endpoint an uptime pinger
(e.g. UptimeRobot) can hit every few minutes.

Not needed if you deploy in webhook mode (WEBHOOK_URL set) — that already
binds to PORT on its own — or on hosts that support real background workers.
"""

from threading import Thread

from flask import Flask

from config import PORT

app = Flask(__name__)


@app.route("/")
def home():
    return "I'm alive!"


def _run():
    app.run(host="0.0.0.0", port=PORT)


def keep_alive():
    Thread(target=_run, daemon=True).start()
