"""
Coin (gold) transfers and owner gifting on top of the Society Builder economy.
Reuses each user's `gold` balance from games.society.
"""

from games import society


def transfer_gold(
    sender_id: int, sender_name: str, receiver_id: int, receiver_name: str, amount: int
) -> dict:
    # Sync both sides to the current time first so balances are up to date
    # before checking affordability.
    society.collect(sender_id, sender_name)
    society.collect(receiver_id, receiver_name)

    sender = society.get_society(sender_id, sender_name)
    receiver = society.get_society(receiver_id, receiver_name)

    if sender["gold"] < amount:
        return {"ok": False, "balance": sender["gold"]}

    sender["gold"] -= amount
    receiver["gold"] += amount

    return {"ok": True, "sender_balance": sender["gold"], "receiver_balance": receiver["gold"]}


def grant_gold(receiver_id: int, receiver_name: str, amount: int) -> dict:
    society.collect(receiver_id, receiver_name)
    receiver = society.get_society(receiver_id, receiver_name)
    receiver["gold"] += amount
    return {"ok": True, "balance": receiver["gold"]}
