import time

from telegram import Update
from telegram.ext import ContextTypes

import admin
from games import economy, relationships, society


def _display_name(user) -> str:
    return user.first_name or user.username or "Traveler"


def _default_name(update: Update) -> str:
    return f"{_display_name(update.effective_user)}'s Society"


def _get_reply_target(update: Update):
    """Returns the User the sender replied to, or None."""
    msg = update.message.reply_to_message
    return msg.from_user if msg and msg.from_user else None


async def society_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = _default_name(update)
    society.collect(user_id, name)  # silently apply any idle production
    soc = society.get_society(user_id, name)

    lines = [
        f"🏙️ {soc['name']}",
        f"👥 Population: {soc['population']}/{society.max_population(soc)}",
        f"🌾 Food: {int(soc['food'])} (+{society.food_rate(soc):.0f}/hr)",
        f"💰 Gold: {int(soc['gold'])} (+{society.gold_rate(soc):.0f}/hr)",
        "",
        "🏗️ Buildings:",
    ]
    for b, count in soc["buildings"].items():
        lines.append(f"  • {b.capitalize()}: {count}")
    lines.append("")
    lines.append("/build <house|farm|market> — construct a building")
    lines.append("/collect — claim resources produced since your last check-in")
    lines.append("/leaderboard — see the top societies")

    await update.message.reply_text("\n".join(lines))


async def society_collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = _default_name(update)
    result = society.collect(user_id, name)

    if result["hours"] <= 0:
        await update.message.reply_text("Nothing new to collect yet — check back in a bit!")
        return

    lines = [f"⏱️ {result['hours']:.1f}h of production collected:"]
    gold_sign = "+" if result["gold_delta"] >= 0 else ""
    food_sign = "+" if result["food_delta"] >= 0 else ""
    lines.append(f"💰 Gold {gold_sign}{result['gold_delta']:.0f}")
    lines.append(f"🌾 Food {food_sign}{result['food_delta']:.0f}")
    if result["pop_delta"] != 0:
        pop_sign = "+" if result["pop_delta"] > 0 else ""
        lines.append(f"👥 Population {pop_sign}{result['pop_delta']}")
    if result["starved"]:
        lines.append("⚠️ You ran out of food and some villagers left — build more farms!")

    await update.message.reply_text("\n".join(lines))


async def society_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = _default_name(update)
    society.collect(user_id, name)  # sync resources before checking affordability

    if not context.args:
        options = "\n".join(f"• {b} — {info['desc']}" for b, info in society.BUILDINGS.items())
        await update.message.reply_text(f"Build what? Usage: /build <name>\n\n{options}")
        return

    building = context.args[0].lower()
    result = society.build(user_id, name, building)

    if not result["ok"]:
        if result["reason"] == "unknown":
            await update.message.reply_text(
                "I don't know that building. Options: " + ", ".join(society.BUILDINGS)
            )
        else:
            await update.message.reply_text(
                f"Not enough resources! Need 💰{result['gold_cost']} / 🌾{result['food_cost']}.")
        return

    await update.message.reply_text(
        f"🏗️ Built a {building}! You now have {result['count']}. "
        f"(-💰{result['gold_cost']} -🌾{result['food_cost']})"
    )


async def society_rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /rename <new society name>")
        return
    name = " ".join(context.args)
    society.get_society(update.effective_user.id, _default_name(update))
    society.rename_society(update.effective_user.id, name)
    await update.message.reply_text(f'Your society is now called "{name}"!')


async def society_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = society.leaderboard()
    if not top:
        await update.message.reply_text("No societies founded yet — start yours with /society!")
        return

    lines = ["🏆 Top Societies:"]
    for i, (_, soc) in enumerate(top, start=1):
        lines.append(f"{i}. {soc['name']} — 👥{soc['population']} 💰{int(soc['gold'])}")

    await update.message.reply_text("\n".join(lines))


# --- Coin transfer & gifting ---


async def give_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user = _get_reply_target(update)
    if not target_user:
        await update.message.reply_text(
            "Reply to the person's message with /give <amount> to send them coins."
        )
        return

    sender = update.effective_user
    if target_user.id == sender.id:
        await update.message.reply_text("You can't send coins to yourself!")
        return
    if target_user.is_bot:
        await update.message.reply_text("You can't send coins to a bot.")
        return
    if not context.args or not context.args[0].isdigit() or int(context.args[0]) <= 0:
        await update.message.reply_text("Usage: reply to someone with /give <amount>")
        return

    amount = int(context.args[0])
    result = economy.transfer_gold(
        sender.id,
        _default_name(update),
        target_user.id,
        f"{_display_name(target_user)}'s Society",
        amount,
    )

    if not result["ok"]:
        await update.message.reply_text(f"You don't have enough gold! (balance: 💰{result['balance']:.0f})")
        return

    await update.message.reply_text(
        f"💸 Sent 💰{amount} to {_display_name(target_user)}! "
        f"Your new balance: 💰{result['sender_balance']:.0f}"
    )


async def grant_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin.is_sudo(update.effective_user.id):
        await update.message.reply_text("Only my owner or a sudo user can use this command!")
        return

    target_user = _get_reply_target(update)
    if not target_user:
        await update.message.reply_text("Reply to someone's message with /grant <amount>.")
        return
    if not context.args or not context.args[0].isdigit() or int(context.args[0]) <= 0:
        await update.message.reply_text("Usage: reply to someone with /grant <amount>")
        return

    amount = int(context.args[0])
    result = economy.grant_gold(target_user.id, f"{_display_name(target_user)}'s Society", amount)

    await update.message.reply_text(
        f"👑 Granted 💰{amount} to {_display_name(target_user)}. "
        f"Their new balance: 💰{result['balance']:.0f}"
    )


# --- Relationship system ---


async def propose_relation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user = _get_reply_target(update)
    if not target_user:
        await update.message.reply_text(
            "Reply to someone's message with /propose to ask them into a relationship!"
        )
        return

    proposer = update.effective_user
    if target_user.id == proposer.id:
        await update.message.reply_text("You can't propose to yourself! (o_o)")
        return
    if target_user.is_bot:
        await update.message.reply_text("They're a bot — probably not relationship material 😅")
        return

    result = relationships.propose(
        proposer.id, _display_name(proposer), target_user.id, _display_name(target_user)
    )
    if not result["ok"]:
        await update.message.reply_text(result["message"])
        return

    await update.message.reply_text(
        f"💌 {_display_name(proposer)} proposed to {_display_name(target_user)}!\n"
        f"{_display_name(target_user)}, reply with /accept or /reject."
    )


async def accept_relation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = relationships.accept(update.effective_user.id)
    if not result["ok"]:
        await update.message.reply_text(result["message"])
        return
    await update.message.reply_text(f"💞 {result['a_name']} and {result['b_name']} are now together!")


async def reject_relation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = relationships.reject(update.effective_user.id)
    await update.message.reply_text(result["message"])


async def breakup_relation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = relationships.breakup(update.effective_user.id)
    await update.message.reply_text(result["message"])


async def relation_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = relationships.get_relation(update.effective_user.id)
    if not info:
        await update.message.reply_text(
            "You're not in a relationship yet. Reply to someone with /propose!"
        )
        return

    days = (time.time() - info["since"]) / 86400
    await update.message.reply_text(
        f"💕 You're with {info['partner_name']} — together for {days:.1f} day(s).\n"
        "Use /breakup if things don't work out."
    )
