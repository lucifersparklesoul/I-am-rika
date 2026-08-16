"""
Bot administration: sudo users, developer users, and global ban (gban).

Permission tiers:
- Owner  (config.OWNER_ID) — full control, can manage sudo/developer lists.
- Sudo   — owner + anyone added via /addsudo. Can gban/ungban and /banall,
           and gets the same economy powers as the owner (e.g. /grant).
- Developer — owner + anyone added via /adddev. Informational tier for
           people who help maintain the bot; doesn't grant moderation power
           by itself, just tracked separately so you can tell mods from devs.

All lists are in-memory and reset if the bot restarts — the owner and any
IDs in SUDO_USER_IDS / DEVELOPER_USER_IDS (.env) are always re-seeded on
startup. Swap this for a real database if you want runtime changes (added
via /addsudo etc.) to survive a restart.
"""

from config import OWNER_ID

_owner_id = int(OWNER_ID) if OWNER_ID and OWNER_ID.isdigit() else None

SUDO_USERS: set[int] = set()
DEVELOPER_USERS: set[int] = set()

# user_id -> reason
GBANNED: dict[int, str] = {}

# chat_id -> set of user_ids seen messaging in that chat. Telegram's Bot API
# has no method to list a group's full membership, so /banall can only act
# on members the bot has actually observed sending a message.
CHAT_MEMBERS_SEEN: dict[int, set[int]] = {}


def _parse_ids(raw: str) -> set[int]:
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def seed_from_env(sudo_raw: str, dev_raw: str) -> None:
    SUDO_USERS.update(_parse_ids(sudo_raw))
    DEVELOPER_USERS.update(_parse_ids(dev_raw))


def is_owner(user_id: int) -> bool:
    return _owner_id is not None and user_id == _owner_id


def is_sudo(user_id: int) -> bool:
    return is_owner(user_id) or user_id in SUDO_USERS


def is_developer(user_id: int) -> bool:
    return is_owner(user_id) or user_id in DEVELOPER_USERS


def add_sudo(user_id: int) -> bool:
    if user_id in SUDO_USERS:
        return False
    SUDO_USERS.add(user_id)
    return True


def remove_sudo(user_id: int) -> bool:
    if user_id not in SUDO_USERS:
        return False
    SUDO_USERS.discard(user_id)
    return True


def add_developer(user_id: int) -> bool:
    if user_id in DEVELOPER_USERS:
        return False
    DEVELOPER_USERS.add(user_id)
    return True


def remove_developer(user_id: int) -> bool:
    if user_id not in DEVELOPER_USERS:
        return False
    DEVELOPER_USERS.discard(user_id)
    return True


def gban(user_id: int, reason: str) -> None:
    GBANNED[user_id] = reason or "No reason given"


def ungban(user_id: int) -> bool:
    if user_id not in GBANNED:
        return False
    del GBANNED[user_id]
    return True


def is_gbanned(user_id: int) -> bool:
    return user_id in GBANNED


def track_chat_member(chat_id: int, user_id: int) -> None:
    CHAT_MEMBERS_SEEN.setdefault(chat_id, set()).add(user_id)


def known_members(chat_id: int) -> set[int]:
    return set(CHAT_MEMBERS_SEEN.get(chat_id, set()))
