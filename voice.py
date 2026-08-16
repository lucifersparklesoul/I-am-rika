"""
Text-to-speech: generates a voice reply using Microsoft Edge's free neural
TTS (via the edge-tts package — no API key needed), then converts it to
Ogg/Opus so Telegram displays it as a proper round voice-note bubble instead
of a generic audio file attachment. Requires ffmpeg to be installed.
"""

import asyncio
import os
import subprocess
import uuid

import edge_tts

from config import DOWNLOAD_DIR, TTS_PITCH, TTS_RATE, TTS_VOICE

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def _synthesize_mp3(text: str, mp3_path: str) -> None:
    communicate = edge_tts.Communicate(text, voice=TTS_VOICE, rate=TTS_RATE, pitch=TTS_PITCH)
    await communicate.save(mp3_path)


def _convert_to_ogg(mp3_path: str, ogg_path: str) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            mp3_path,
            "-c:a",
            "libopus",
            "-b:a",
            "64k",
            "-vbr",
            "on",
            "-application",
            "voip",
            ogg_path,
        ],
        check=True,
        capture_output=True,
    )


async def text_to_voice_note(text: str) -> str:
    """Generates a voice note for `text` and returns the path to an .ogg file.

    Raises on failure (missing edge-tts network access, ffmpeg not installed,
    etc.) — callers should catch and fall back to a text reply.
    """
    base = os.path.join(DOWNLOAD_DIR, uuid.uuid4().hex)
    mp3_path = f"{base}.mp3"
    ogg_path = f"{base}.ogg"

    try:
        await _synthesize_mp3(text, mp3_path)
        await asyncio.to_thread(_convert_to_ogg, mp3_path, ogg_path)
    finally:
        if os.path.exists(mp3_path):
            os.remove(mp3_path)

    return ogg_path
