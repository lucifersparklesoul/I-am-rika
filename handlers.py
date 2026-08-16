import logging
import os
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import voice
from config import BOT_NAME, MAX_HISTORY_TURNS, OWNER_ID, SUPPORT_CHAT_URL, UPDATE_CHANNEL_URL
from persona import _histories, chat_reply, get_profile, mark_awaiting_intro, save_intro

logger = logging.getLogger(__name__)

START_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "assets", "start_image.png")

# Matches the bot's name as a whole word, case-insensitive — used so group
# chats only get a reply when someone actually calls out to the bot by name.
NAME_PATTERN = re.compile(rf"\b{re.escape(BOT_NAME)}\b", re.IGNORECASE)

# Phrases that signal "answer me with a voice note" rather than plain text.
VOICE_TRIGGERS = (
    "voice note",
    "voice message",
    "voice reply",
    "in voice",
    "as a voice",
    "send voice",
    "send a voice",
    "audio note",
    "audio message",
    "speak it",
    "say it out loud",
    "reply in voice",
    "voice please",
    "voice version",
)


def wants_voice(text: str) -> bool:
    lowered = text.lower()
    return any(trigger in lowered for trigger in VOICE_TRIGGERS)


def _start_keyboard() -> InlineKeyboardMarkup | None:
    buttons = []
    if SUPPORT_CHAT_URL:
        buttons.append(InlineKeyboardButton("💬 Support Chat", url=SUPPORT_CHAT_URL))
    if UPDATE_CHANNEL_URL:
        buttons.append(InlineKeyboardButton("📢 Update Channel", url=UPDATE_CHANNEL_URL))
    if OWNER_ID:
        buttons.append(InlineKeyboardButton("👑 Owner", url=f"tg://user?id={OWNER_ID}"))

    if not buttons:
        return None

    # One button per row so labels stay readable on mobile.
    return InlineKeyboardMarkup([[b] for b in buttons])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        f"Hiii, I'm {BOT_NAME}! (o^▽^o)\n\n"
        "Talk to me anytime and I'll chat with you.\n"
        "Ask me to \"send a voice note\" and I'll answer out loud!\n"
        "Try /society to found your own city and start building!\n"
        "Use /help to see everything I can do."
    )
    if os.path.exists(START_IMAGE_PATH):
        with open(START_IMAGE_PATH, "rb") as photo:
            await update.message.reply_photo(
                photo=photo, caption=caption, reply_markup=_start_keyboard()
            )
    else:
        await update.message.reply_text(caption, reply_markup=_start_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Here's what I can do:\n\n"
        "💬 /reset — clear our chat history\n"
        "🎤 /voice <question> — get the answer as a voice note (or just ask "
        "naturally, e.g. \"send me a voice note about...\")\n\n"
        "🏙️ Society Builder game:\n"
        "/society — view your society\n"
        "/build <house|farm|market> — construct a building\n"
        "/collect — claim resources produced over time\n"
        "/rename <name> — rename your society\n"
        "/leaderboard — see the top societies\n\n"
        "💰 Coins (reply to someone's message to use these):\n"
        "/give <amount> — send coins to that person\n\n"
        "💞 Relationships (reply to someone's message):\n"
        "/propose — propose a relationship\n"
        "/accept, /reject — respond to a proposal sent to you\n"
        "/relation — check your relationship status\n"
        "/breakup — end your current relationship\n\n"
        "🛡️ Admin (owner/sudo only) — see the README for the full list, "
        "including /gban, /banall, /addsudo, /adddev.\n\n"
        "Just send me a normal message and I'll reply!"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _histories.pop(update.effective_chat.id, None)
    await update.message.reply_text("Okay, clean slate! What's on your mind? (o^^)o")


async def _reply_with_voice(update: Update, question: str) -> None:
    await update.effective_chat.send_action("record_voice")
    reply_text = await chat_reply(update.effective_chat.id, question, MAX_HISTORY_TURNS, voice_mode=True)

    try:
        ogg_path = await voice.text_to_voice_note(reply_text)
    except Exception:
        logger.exception("Voice note generation failed, falling back to text")
        await update.message.reply_text(reply_text)
        return

    try:
        with open(ogg_path, "rb") as voice_file:
            await update.message.reply_voice(voice=voice_file)
    finally:
        try:
            os.remove(ogg_path)
        except OSError:
            pass


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args) if context.args else None
    if not question:
        await update.message.reply_text("Ask me something! e.g. /voice what's the capital of France?")
        return
    await _reply_with_voice(update, question)


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    tg_chat = update.effective_chat
    user = update.effective_user

    profile = get_profile(user.id)
    awaiting_intro = profile["awaiting"] and not profile["introduced"]

    # In groups, only respond when directly called out to — by name or by
    # replying to one of the bot's own messages — UNLESS we're specifically
    # waiting on this person's answer to the intro question, in which case
    # their very next message counts even without a mention.
    if tg_chat.type != "private" and not awaiting_intro:
        is_mentioned = bool(NAME_PATTERN.search(text))
        replied_to_bot = (
            update.message.reply_to_message is not None
            and update.message.reply_to_message.from_user is not None
            and update.message.reply_to_message.from_user.id == context.bot.id
        )
        if not (is_mentioned or replied_to_bot):
            return

    # First time this person has ever messaged the bot (in any chat): ask
    # them to introduce themselves before chatting for real.
    if not profile["introduced"]:
        if not profile["awaiting"]:
            mark_awaiting_intro(user.id)
            await update.message.reply_text(
                f"Hiii, I'm {BOT_NAME}! (o^▽^o)\n\n"
                "Before we get into it, introduce yourself? Your name, and "
                "however you'd describe yourself (guy/girl/however you like) "
                "so I know how to vibe with you!"
            )
            return
        # This message is their answer — save it and let the conversation
        # continue naturally below.
        save_intro(user.id, tg_chat.id, text)

    if wants_voice(text):
        await _reply_with_voice(update, text)
        return

    await tg_chat.send_action("typing")
    reply = await chat_reply(tg_chat.id, text, MAX_HISTORY_TURNS)
    await update.message.reply_text(reply)
