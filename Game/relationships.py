"""
A simple mutual relationship ("partner") system between users, independent
of the Society Builder game. State is in-memory and resets if the bot
restarts.
"""

import time

# user_id -> {"partner_id": int, "partner_name": str, "since": float}
_relations: dict[int, dict] = {}

# target_user_id -> {"from_id": int, "from_name": str, "to_name": str}
_pending: dict[int, dict] = {}


def is_taken(user_id: int) -> bool:
    return user_id in _relations


def propose(from_id: int, from_name: str, to_id: int, to_name: str) -> dict:
    if is_taken(from_id):
        return {
            "ok": False,
            "message": "You're already in a relationship! Use /breakup first if you want to change that.",
        }
    if is_taken(to_id):
        return {"ok": False, "message": f"{to_name} is already in a relationship!"}
    if to_id in _pending and _pending[to_id]["from_id"] == from_id:
        return {"ok": False, "message": "You already proposed — waiting for their answer!"}

    _pending[to_id] = {"from_id": from_id, "from_name": from_name, "to_name": to_name}
    return {"ok": True}


def accept(user_id: int) -> dict:
    pending = _pending.get(user_id)
    if not pending:
        return {"ok": False, "message": "You don't have any pending proposals."}

    from_id = pending["from_id"]
    now = time.time()
    _relations[user_id] = {
        "partner_id": from_id,
        "partner_name": pending["from_name"],
        "since": now,
    }
    _relations[from_id] = {
        "partner_id": user_id,
        "partner_name": pending["to_name"],
        "since": now,
    }
    del _pending[user_id]

    return {"ok": True, "a_name": pending["from_name"], "b_name": pending["to_name"]}


def reject(user_id: int) -> dict:
    if user_id not in _pending:
        return {"ok": False, "message": "You don't have any pending proposals."}
    del _pending[user_id]
    return {"ok": True, "message": "Proposal declined."}


def breakup(user_id: int) -> dict:
    rel = _relations.get(user_id)
    if not rel:
        return {"ok": False, "message": "You're not in a relationship."}

    partner_id = rel["partner_id"]
    partner_name = rel["partner_name"]
    _relations.pop(user_id, None)
    _relations.pop(partner_id, None)

    return {"ok": True, "message": f"💔 You broke up with {partner_name}."}


def get_relation(user_id: int) -> dict | None:
    return _relations.get(user_id)
