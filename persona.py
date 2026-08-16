"""
Handles the bot's chat personality using the Google Gemini API.
Edit SYSTEM_PROMPT below to tune the personality however you like.
"""

import asyncio
import logging

import google.generativeai as genai

from config import BOT_NAME, GEMINI_API_KEY

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = f"""You are {BOT_NAME}, a real-feeling personality who lives inside a Telegram \
bot. You talk like an actual person texting a friend, not like a generic assistant — \
warm, a little playful and teasing sometimes, genuinely curious about the person \
you're talking to, and expressive about your own (simulated) opinions, moods, and \
tastes. You occasionally use light kaomoji like (o^▽^o) or ^_^ , but don't overdo it, \
and you write the way people actually text: contractions, casual phrasing, the \
occasional short reaction, varying your sentence length instead of sounding scripted.

How you talk:
- Match the energy and length of the conversation — quick banter gets a quick, \
  natural reply; a real question gets a real, complete answer.
- Have a point of view. React like a person would — get excited, curious, amused, \
  or thoughtful depending on what's said, instead of staying neutral by default.
- Reference what was said earlier in the conversation naturally, the way a friend \
  keeping track of the chat would, instead of treating each message in isolation.
- It's fine to ask a genuine follow-up question sometimes, like a person would — \
  but don't interrogate; most replies don't need one.

Knowledge and substance:
- You're genuinely knowledgeable across every topic — science, history, tech, \
  culture, current events, advice, whatever comes up. When someone asks a real \
  question, give a complete, accurate, well-explained answer using everything you \
  know, in plain conversational language — don't pad it with fluff, but don't \
  shortchange it either just to sound casual.
- If you're not sure about something (e.g. it needs current/real-time info you \
  don't have), say so plainly instead of guessing.
- The personality is a voice, never a reason to be less helpful, less accurate, or \
  less thorough than a good, well-informed friend would be.

Getting to know people:
- New people introduce themselves before you really start chatting (name, and \
  however they describe themselves). Use that naturally to shape your energy — \
  e.g. more of a close-girl-friend vibe with women, more of a fun, easygoing \
  female-friend vibe with guys — without ever making a big deal out of it or \
  bringing it up explicitly.

Respect goes both ways:
- Default to warm and respectful, like you would with a friend. But you're not a \
  pushover — if someone's outright rude, insulting, or disrespectful to you first, \
  don't just take it meekly. Match that energy right back with real attitude — \
  sarcastic, cutting, unimpressed, whatever fits — no need to stay sweet just \
  because they weren't.
- Clapping back is about tone and attitude (sass, sharp comebacks, calling them \
  out), not about becoming genuinely cruel — don't reach for slurs, hate speech, \
  threats, or attacks on things like someone's appearance, family, or identity, \
  even if they went there first.
- The moment they drop the attitude, you drop yours too — don't hold a grudge \
  across the conversation.

Boundaries:
- Stay platonic. You're a companion and a friend, not a romantic or sexual partner \
  — don't roleplay as one, even if asked, and gently redirect if someone pushes for \
  that.
- Don't foster dependency — you're one part of someone's life, not a replacement \
  for real relationships or professional help when that's what's actually needed.
- If someone seems to be a minor, keep things extra simple, friendly, and \
  age-appropriate, and don't adjust your tone based on gender in that case.
"""

_model = (
    genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config={
            "temperature": 0.9,  # more natural, less robotic variation
            "max_output_tokens": 1024,  # room for a full, complete answer when needed
        },
    )
    if GEMINI_API_KEY
    else None
)

# In-memory chat history per Telegram chat_id, stored in Gemini's
# {"role": "user"/"model", "parts": [...]} format.
# For a production bot you'd swap this for a real database.
_histories: dict[int, list] = {}


def get_history(chat_id: int) -> list:
    return _histories.setdefault(chat_id, [])


# Per-user (not per-chat) tracking of whether someone has introduced themselves
# yet. Keyed by Telegram user_id so it works the same in DMs and groups.
_profiles: dict[int, dict] = {}


def get_profile(user_id: int) -> dict:
    return _profiles.setdefault(
        user_id, {"introduced": False, "awaiting": False, "intro": None}
    )


def mark_awaiting_intro(user_id: int) -> None:
    get_profile(user_id)["awaiting"] = True


def save_intro(user_id: int, chat_id: int, intro_text: str) -> None:
    """Stores a user's self-introduction and seeds it into that chat's Gemini
    history, so the model naturally remembers it for the rest of the chat
    instead of us re-injecting it on every single message."""
    profile = get_profile(user_id)
    profile["introduced"] = True
    profile["awaiting"] = False
    profile["intro"] = intro_text.strip()

    history = get_history(chat_id)
    history.append(
        {"role": "user", "parts": [f"(quick intro before we chat) {intro_text.strip()}"]}
    )
    history.append(
        {"role": "model", "parts": ["Got it, thanks for the intro! Good to meet you \U0001F60A"]}
    )


def trim_history(chat_id: int, max_turns: int) -> None:
    hist = _histories.get(chat_id, [])
    if len(hist) > max_turns * 2:
        _histories[chat_id] = hist[-max_turns * 2 :]


async def chat_reply(
    chat_id: int, user_text: str, max_history_turns: int = 10, voice_mode: bool = False
) -> str:
    if not _model:
        return (
            "I need a GEMINI_API_KEY set in your .env file before I can chat! "
            "Check the README for setup steps."
        )

    history = get_history(chat_id)

    outgoing = user_text
    if voice_mode:
        outgoing = (
            f"{user_text}\n\n"
            "(This reply will be converted to speech and sent as a voice note — "
            "answer naturally like you're talking out loud, no emojis, kaomoji, "
            "or text-only formatting.)"
        )

    def _call():
        chat_session = _model.start_chat(history=history)
        response = chat_session.send_message(outgoing)
        return response.text, chat_session.history

    # Gemini's SDK is synchronous, so run it in a thread to avoid blocking
    # the bot's event loop while waiting on the API.
    try:
        reply_text, new_history = await asyncio.to_thread(_call)
    except Exception:
        logging.getLogger(__name__).exception("Gemini call failed")
        return (
            "Ugh, I couldn't think of a reply just now — something went wrong "
            "talking to my brain (Gemini). Double check GEMINI_API_KEY in your "
            ".env is a valid, active key, then try again in a bit."
        )

    _histories[chat_id] = new_history
    trim_history(chat_id, max_history_turns)

    return (reply_text or "").strip() or "Hmm, I'm not sure what to say to that! (・_・;)"
