import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_NAME = os.getenv("BOT_NAME", "Yuki")
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "10"))
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")

# --- /start button links ---
OWNER_ID = os.getenv("OWNER_ID", "").strip()
SUPPORT_CHAT_URL = os.getenv("SUPPORT_CHAT_URL", "").strip()
UPDATE_CHANNEL_URL = os.getenv("UPDATE_CHANNEL_URL", "").strip()

# --- Admin tiers ---
# Comma-separated numeric Telegram user IDs, e.g. "111111,222222". The owner
# (OWNER_ID above) always has sudo + developer power automatically.
SUDO_USER_IDS = os.getenv("SUDO_USER_IDS", "").strip()
DEVELOPER_USER_IDS = os.getenv("DEVELOPER_USER_IDS", "").strip()

# --- Voice notes (text-to-speech) ---
# Any edge-tts neural voice name works; a few cute/young-sounding options:
# en-US-AnaNeural (child-like, default), en-US-JennyNeural, en-GB-SoniaNeural,
# ja-JP-NanamiNeural. Full list: `edge-tts --list-voices`.
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AnaNeural")
TTS_RATE = os.getenv("TTS_RATE", "+0%")
TTS_PITCH = os.getenv("TTS_PITCH", "+15%")  # higher pitch = cuter/younger-sounding

# --- Hosting-related settings ---
# Most free hosts assign a port via the PORT env var and expect the app to
# bind to it (this keeps the service classified as "web" instead of being
# killed as idle). Defaults to 8080 for local/dev use.
PORT = int(os.getenv("PORT", "8080"))

# If set (e.g. https://your-app.onrender.com), the bot runs in webhook mode
# and binds to PORT directly — best for platforms like Render/Railway that
# require the app to serve HTTP. Leave empty to use polling instead.
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

# When running in polling mode on a host that needs an open port to stay
# alive (e.g. Replit + UptimeRobot), this starts a tiny Flask "I'm alive"
# server alongside the bot. Has no effect in webhook mode. Set to "false" to
# disable.
ENABLE_KEEPALIVE = os.getenv("ENABLE_KEEPALIVE", "true").lower() == "true"

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in."
    )
