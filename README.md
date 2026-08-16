# Telegram Girl-AI Bot

A Telegram bot with a chat personality, an idle city-building game, coin
transfers, and a relationship system.

1. **Chat personality** — talks with a warm, cheerful "girl next door" vibe, powered by the Google Gemini API.
2. **Society Builder** — a small idle city-building game playable through commands.
3. **Coins & relationships** — send coins to other users, and propose/accept a "partner" relationship.

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) installed and on your PATH (needed to package voice note replies)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A [Gemini API key](https://aistudio.google.com/apikey) (free tier available)

### Installing ffmpeg
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: download from ffmpeg.org and add it to your PATH

## Setup

```bash
git clone <this repo>
cd telegram-girl-ai-bot
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill in:

```
TELEGRAM_BOT_TOKEN=123456:ABC-your-bot-token
GEMINI_API_KEY=AIza...
BOT_NAME=Yuki
```

### Getting a Telegram bot token
1. Open Telegram, message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token it gives you into `.env`

## Run

```bash
python main.py
```

The bot will start polling Telegram for messages. Open a chat with your bot and try:

- `/start` — greeting
- Any normal message — the bot replies in character
- `/reset` — clears the chat's conversation history
- `/society` — try the game (see below)

## Voice notes

Ask naturally (e.g. "send me a voice note about black holes", "can you reply "
"in voice?") or use `/voice <question>` directly, and the bot answers with a
real voice-note bubble instead of text — same knowledge, same personality,
just spoken.

- **Detection**: the chat handler checks the message for phrases like "voice
  note", "in voice", "send voice", etc. (`VOICE_TRIGGERS` in `handlers.py` —
  edit that list to add more trigger phrases). `/voice <question>` always
  works regardless of phrasing.
- **Voice**: generated with [edge-tts](https://github.com/rany2/edge-tts)
  (Microsoft Edge's free neural TTS, no API key needed). Pick the voice via
  `TTS_VOICE` in `.env` — `en-US-AnaNeural` (default) is a young/child-like
  voice for a "cute girl" feel; try `en-US-JennyNeural`, `en-GB-SoniaNeural`,
  or `ja-JP-NanamiNeural` for other tones. `TTS_PITCH` (default `+15%`) nudges
  the pitch up for a cuter sound; `TTS_RATE` controls speaking speed.
- **Format**: the raw TTS output is converted to Ogg/Opus via `ffmpeg` so
  Telegram renders it as an actual voice message (round bubble, waveform),
  not a generic audio attachment — this is why `ffmpeg` is a requirement.
- If TTS or the ffmpeg conversion fails for any reason, the bot automatically
  falls back to a normal text reply instead of erroring out silently.

## Society Builder game

A lightweight idle city-building game playable entirely through commands:

- `/society` — view your society (auto-founds one the first time you use it)
- `/build <house|farm|market>` — construct a building
  - **house** — +10 max population
  - **farm** — +10 food/hour
  - **market** — +8 gold/hour
- `/collect` — claim resources produced since you last checked in
- `/rename <name>` — rename your society
- `/leaderboard` — see the top societies by population

Resources accrue passively based on real elapsed time — food and gold both
grow between check-ins, and population grows when there's a food surplus but
shrinks if food runs out, so farms need to keep pace with population. Each
Telegram user has their own society (works the same in DMs and group chats).
Building costs increase 15% each time you build another of the same type.

Game state lives in memory (`games/society.py`) and resets if the bot
restarts, same as chat history — swap it for SQLite/Redis/etc. if you want
progress to persist.

## Coin transfer & owner gifting

Users can send each other gold from the Society Builder economy, and the
bot owner can gift gold for free. Both require **replying** to the target
person's message (this is how the bot reliably identifies who you mean,
without needing usernames or a user database):

- `/give <amount>` — reply to someone's message to send them that many coins
- `/grant <amount>` — owner-only (checked against `OWNER_ID` in `.env`);
  reply to someone's message to gift them coins for free

## Relationship system

A lightweight "partner" system, independent of the Society Builder game —
also uses reply-to-message to target someone:

- `/propose` — reply to someone's message to propose a relationship
- `/accept` / `/reject` — the other person responds to a pending proposal
- `/relation` — check your current relationship status
- `/breakup` — end your current relationship

Only one relationship per person at a time; state resets on restart, same
as everything else in-memory.

## Admin & moderation

Three permission tiers, seeded from `.env` and extendable at runtime:

- **Owner** — whoever's ID is in `OWNER_ID`. Full control, including
  managing the sudo and developer lists.
- **Sudo** — the owner, plus anyone in `SUDO_USER_IDS` or added via
  `/addsudo`. Gets moderation power (gban, banall) and the same economy
  power as the owner (e.g. `/grant`).
- **Developer** — the owner, plus anyone in `DEVELOPER_USER_IDS` or added
  via `/adddev`. A separate, informational tier for people who help
  maintain the bot; doesn't grant moderation power by itself.

Owner-only:
- `/addsudo` / `/delsudo` (reply or `<user id>`) — manage sudo users
- `/sudolist` — list current sudo users
- `/adddev` / `/deldev` (reply or `<user id>`) — manage developers
- `/devlist` — list current developers

Sudo-only:
- `/gban <reason>` (reply to a user) — globally ban them: deletes their
  messages and bans them from any group the bot administers, enforced as
  they're seen active in each chat (see the limitation note below)
- `/ungban` (reply or `<user id>`) — remove a global ban
- `/gbanlist` — list everyone currently gbanned
- `/banall` — mass-ban known members of the **current group** (see below)

**Limitation to know about:** Telegram's Bot API has no method for a bot to
list a group's full membership. So:
- `/gban` bans the target immediately in the chat where you ran the
  command, and then bans them anywhere else the bot is admin **the next
  time they send a message there** — it can't reach chats they're already
  silent in.
- `/banall` only bans users the bot has actually seen post a message in
  that group while it was running (tracked in `admin.py`'s
  `CHAT_MEMBERS_SEEN`) — not literally every member of the group. A true
  "ban every member regardless of activity" would require a full userbot
  (Pyrogram/Telethon with an authenticated user session) instead of the
  Bot API, which is a heavier, more fragile, and more ToS-sensitive setup
  not included here.

All admin state (`admin.py`) is in-memory and reset on restart, except the
owner and any IDs already in `.env`, which are re-seeded automatically.

## Project structure

```
telegram-girl-ai-bot/
├── main.py         # entry point, registers handlers, starts polling/webhook
├── handlers.py     # command & message handler functions
├── persona.py      # chat personality + Gemini API calls
├── voice.py        # text-to-speech + ffmpeg conversion for voice notes
├── admin.py         # sudo/developer tiers + global ban registry
├── admin_handlers.py # sudo/dev/gban/banall Telegram command handlers
├── games/
│   ├── society.py       # Society Builder game logic/state
│   ├── economy.py       # coin transfer & owner gifting
│   ├── relationships.py # propose/accept/breakup relationship system
│   └── handlers.py      # Telegram command handlers for all of the above
├── assets/
│   └── start_image.png
├── keep_alive.py   # tiny Flask "I'm alive" server for free-tier hosts
├── config.py       # loads settings from .env
├── Dockerfile      # for Docker-based free hosts (Render, Railway, Fly.io)
├── Procfile        # for buildpack-based hosts
├── runtime.txt     # pinned Python version for buildpack hosts
├── requirements.txt
├── .env.example
├── .dockerignore
└── .gitignore
```

## Free hosting

Most free web services expect the app to bind to a `PORT` and answer HTTP
requests (or they get shut down as "idle"). This repo handles that either way:

- **Webhook vs polling** — set `WEBHOOK_URL` to your deployed URL and the bot
  binds directly to `PORT` and serves Telegram updates over HTTP (ideal for
  "web service" style free hosts). Leave it empty to use polling instead — in
  that case the bot starts a small Flask "I'm alive" page on `PORT` too
  (`keep_alive.py`), controlled by `ENABLE_KEEPALIVE`, so ping/uptime
  services can keep it awake.
- **Docker** — the included `Dockerfile` works on any Docker-friendly free
  host with no extra system packages needed.

### Render (free web service, Docker)
1. Push this repo to GitHub.
2. Render → New → Web Service → connect the repo → environment: **Docker**.
3. Add environment variables: `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`,
   `WEBHOOK_URL` = `https://<your-render-app>.onrender.com` (you'll know the
   exact URL after the first deploy — set it, then redeploy).
4. Render sets `PORT` automatically — no need to add it yourself.
5. Deploy. The bot runs in webhook mode and serves requests directly.

### Railway (free trial credits, Docker or Nixpacks)
1. Push to GitHub, then Railway → New Project → Deploy from repo.
2. Railway auto-detects the `Dockerfile`. Add the same env vars as above,
   including `WEBHOOK_URL` set to your Railway-generated domain.
3. Railway also sets `PORT` automatically.

### Replit (polling mode + keep-alive)
1. Import this repo into a new Repl (Python).
2. Add `TELEGRAM_BOT_TOKEN` and `GEMINI_API_KEY` as Replit **Secrets**.
   Leave `WEBHOOK_URL` empty so it runs in polling mode.
3. Run the repl, then point a free uptime pinger (e.g. UptimeRobot) at your
   Repl's web URL every 5 minutes so it doesn't spin down.

### Fly.io (free allowance, Docker)
1. Install `flyctl`, run `fly launch` in this folder (it will detect the
   `Dockerfile`).
2. `fly secrets set TELEGRAM_BOT_TOKEN=... GEMINI_API_KEY=... WEBHOOK_URL=https://<your-app>.fly.dev`
3. `fly deploy`

### General tips for any free host
- Free tiers usually have **ephemeral storage** — nothing in this bot relies
  on persistent disk.
- Chat history and game state live in memory and reset whenever the free
  instance restarts/sleeps. If you need them to persist, swap the relevant
  in-memory dicts (`persona.py`'s `_histories`, `games/society.py`'s
  `_societies`, etc.) for SQLite or a free hosted database (e.g. Supabase,
  Neon, Upstash Redis).

## Customizing the /start buttons

`/start` shows up to three inline buttons under the welcome image, controlled
by env vars — leave any of them blank to hide that button:

```
OWNER_ID=123456789            # numeric Telegram user ID, opens a chat with the owner
SUPPORT_CHAT_URL=https://t.me/your_support_chat
UPDATE_CHANNEL_URL=https://t.me/your_update_channel
```

The owner button uses a `tg://user?id=...` deep link rather than a normal
`https://t.me/...` link, since numeric user IDs (unlike usernames) don't have
a public profile URL — this only works if the recipient's Telegram client has
seen that user before (e.g. via a shared group), which is normal for a bot
owner.

## Customizing the personality

Edit `SYSTEM_PROMPT` in `persona.py`. This is a plain-text prompt describing tone,
boundaries, and behavior — change the name, tone, emoji use, or add extra rules
(e.g. always answer in a certain language) as you like. The included default is
intentionally kept friendly and platonic (a helpful companion, not a romantic
roleplay character) — if you adjust it, keep in mind Telegram's own bot content
policies apply to whatever your bot publishes.

## Notes & limitations

- Chat history is stored in memory per chat and resets when the bot restarts.
  Swap `persona.py`'s `_histories` dict for a real database (SQLite, Redis, etc.)
  if you need persistence.
- Society, coin, and relationship state are similarly in-memory — same caveat.
- For production, consider running the bot as a systemd service or in Docker,
  and using webhooks instead of polling for better scalability.
