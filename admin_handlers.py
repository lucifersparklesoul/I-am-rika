from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

import admin


def _resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Returns (user_id, label) from a reply-to-message or a numeric arg, or (None, None)."""
    msg = update.message.reply_to_message
    if msg and msg.from_user:
        user = msg.from_user
        return user.id, (user.first_name or user.username or str(user.id))
    if context.args and context.args[0].isdigit():
        uid = int(context.args[0])
        return uid, str(uid)
    return None, None


# --- Sudo management (owner-only) ---


async def add_sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin.is_owner(update.effective_user.id):
        await update.message.reply_text("Only my owner can manage sudo users.")
        return
    user_id, label = _resolve_target(update, context)
    if user_id is None:
        await update.message.reply_text("Reply to someone or give a user ID: /addsudo <id>")
        return
    added = admin.add_sudo(user_id)
    await update.message.reply_text(
        f"✅ {label} is now a sudo user." if added else f"{label} is already a sudo user."
    )


async def del_sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin.is_owner(update.effective_user.id):
        await update.message.reply_text("Only my owner can manage sudo users.")
        return
    user_id, label = _resolve_target(update, context)
    if user_id is None:
        await update.message.reply_text("Reply to someone or give a user ID: /delsudo <id>")
        return
    removed = admin.remove_sudo(user_id)
    await update.message.reply_text(
        f"❌ Removed {label} from sudo users." if removed else f"{label} isn't a sudo user."
    )


async def sudo_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ids = sorted(admin.SUDO_USERS)
    if not ids:
        await update.message.reply_text("No extra sudo users added yet (the owner always has sudo power).")
        return
    lines = ["👤 Sudo users:"] + [f"• `{uid}`" for uid in ids]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# --- Developer management (owner-only) ---


async def add_dev_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin.is_owner(update.effective_user.id):
        await update.message.reply_text("Only my owner can manage developers.")
        return
    user_id, label = _resolve_target(update, context)
    if user_id is None:
        await update.message.reply_text("Reply to someone or give a user ID: /adddev <id>")
        return
    added = admin.add_developer(user_id)
    await update.message.reply_text(
        f"✅ {label} is now a developer." if added else f"{label} is already a developer."
    )


async def del_dev_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin.is_owner(update.effective_user.id):
        await update.message.reply_text("Only my owner can manage developers.")
        return
    user_id, label = _resolve_target(update, context)
    if user_id is None:
        await update.message.reply_text("Reply to someone or give a user ID: /deldev <id>")
        return
    removed = admin.remove_developer(user_id)
    await update.message.reply_text(
        f"❌ Removed {label} from developers." if removed else f"{label} isn't a developer."
    )


async def dev_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ids = sorted(admin.DEVELOPER_USERS)
    if not ids:
        await update.message.reply_text("No extra developers added yet (the owner is always a developer).")
        return
    lines = ["🛠️ Developers:"] + [f"• `{uid}`" for uid in ids]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# --- Global ban (sudo-only) ---


async def gban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin.is_sudo(update.effective_user.id):
        await update.message.reply_text("Only sudo users can globally ban.")
        return

    msg = update.message.reply_to_message
    if not msg or not msg.from_user:
        await update.message.reply_text("Reply to the user's message with /gban <reason>.")
        return

    target = msg.from_user
    if admin.is_sudo(target.id):
        await update.message.reply_text("You can't gban a sudo user.")
        return

    reason = " ".join(context.args) if context.args else "No reason given"
    admin.gban(target.id, reason)

    # Best-effort immediate ban in the current chat; full "global" reach
    # happens opportunistically as they're seen in other chats (see the
    # gban_enforcement middleware).
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
    except Exception:
        pass

    await update.message.reply_text(
        f"🚫 Globally banned {target.first_name or target.id}. Reason: {reason}\n"
        "They'll be auto-removed from any group this bot administers as soon "
        "as they're active there."
    )


async def ungban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin.is_sudo(update.effective_user.id):
        await update.message.reply_text("Only sudo users can undo a global ban.")
        return
    user_id, label = _resolve_target(update, context)
    if user_id is None:
        await update.message.reply_text("Reply to someone or give a user ID: /ungban <id>")
        return
    removed = admin.ungban(user_id)
    await update.message.reply_text(
        f"✅ {label} was un-gbanned." if removed else f"{label} wasn't gbanned."
    )


async def gban_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin.GBANNED:
        await update.message.reply_text("No one is globally banned.")
        return
    lines = ["🚫 Globally banned users:"]
    for uid, reason in admin.GBANNED.items():
        lines.append(f"• `{uid}` — {reason}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# --- Mass ban (sudo-only) ---


async def ban_all_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin.is_sudo(update.effective_user.id):
        await update.message.reply_text("Only sudo users can use /banall.")
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("This only works in groups.")
        return

    targets = admin.known_members(chat.id)
    targets.discard(update.effective_user.id)
    targets = {uid for uid in targets if not admin.is_sudo(uid)}

    if not targets:
        await update.message.reply_text(
            "I don't have anyone tracked in this chat to ban yet. Telegram's Bot API "
            "doesn't let bots list a group's full membership — I can only act on members "
            "who have sent at least one message here while I was around."
        )
        return

    status = await update.message.reply_text(f"🚫 Banning {len(targets)} known member(s)...")
    banned, failed = 0, 0
    for uid in targets:
        try:
            await context.bot.ban_chat_member(chat.id, uid)
            banned += 1
        except Exception:
            failed += 1

    await status.edit_text(f"✅ Done. Banned {banned}, failed {failed}.")


# --- Middleware: tracks chat membership and enforces gban on every message ---


async def gban_enforcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.effective_chat:
        return

    chat = update.effective_chat
    user = update.effective_user

    if chat.type in ("group", "supergroup"):
        admin.track_chat_member(chat.id, user.id)

    if admin.is_gbanned(user.id):
        if update.message:
            try:
                await update.message.delete()
            except Exception:
                pass
        if chat.type in ("group", "supergroup"):
            try:
                await context.bot.ban_chat_member(chat.id, user.id)
            except Exception:
                pass
        raise ApplicationHandlerStop
