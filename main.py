import logging

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

import admin
from admin_handlers import (
    add_dev_cmd,
    add_sudo_cmd,
    ban_all_cmd,
    del_dev_cmd,
    del_sudo_cmd,
    dev_list_cmd,
    gban_cmd,
    gban_enforcement,
    gban_list_cmd,
    sudo_list_cmd,
    ungban_cmd,
)
from config import (
    DEVELOPER_USER_IDS,
    ENABLE_KEEPALIVE,
    PORT,
    SUDO_USER_IDS,
    TELEGRAM_BOT_TOKEN,
    WEBHOOK_URL,
)
from games.handlers import (
    accept_relation,
    breakup_relation,
    give_coins,
    grant_coins,
    propose_relation,
    reject_relation,
    relation_status,
    society_build,
    society_collect,
    society_leaderboard,
    society_rename,
    society_status,
)
from handlers import chat, help_command, reset, start, voice_command

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def main():
    admin.seed_from_env(SUDO_USER_IDS, DEVELOPER_USER_IDS)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Runs before every other handler: tracks chat membership and enforces
    # any active global ban (see admin_handlers.gban_enforcement).
    app.add_handler(MessageHandler(filters.ALL, gban_enforcement), group=-1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("voice", voice_command))

    # Society Builder game
    app.add_handler(CommandHandler("society", society_status))
    app.add_handler(CommandHandler("build", society_build))
    app.add_handler(CommandHandler("collect", society_collect))
    app.add_handler(CommandHandler("rename", society_rename))
    app.add_handler(CommandHandler("leaderboard", society_leaderboard))

    # Coin transfer & owner/sudo gifting (reply to a user's message to target them)
    app.add_handler(CommandHandler("give", give_coins))
    app.add_handler(CommandHandler("grant", grant_coins))

    # Relationship system (reply to a user's message to target them)
    app.add_handler(CommandHandler("propose", propose_relation))
    app.add_handler(CommandHandler("accept", accept_relation))
    app.add_handler(CommandHandler("reject", reject_relation))
    app.add_handler(CommandHandler("breakup", breakup_relation))
    app.add_handler(CommandHandler("relation", relation_status))

    # Admin: sudo/developer management (owner-only)
    app.add_handler(CommandHandler("addsudo", add_sudo_cmd))
    app.add_handler(CommandHandler("delsudo", del_sudo_cmd))
    app.add_handler(CommandHandler("sudolist", sudo_list_cmd))
    app.add_handler(CommandHandler("adddev", add_dev_cmd))
    app.add_handler(CommandHandler("deldev", del_dev_cmd))
    app.add_handler(CommandHandler("devlist", dev_list_cmd))

    # Admin: global ban & mass ban (sudo-only)
    app.add_handler(CommandHandler("gban", gban_cmd))
    app.add_handler(CommandHandler("ungban", ungban_cmd))
    app.add_handler(CommandHandler("gbanlist", gban_list_cmd))
    app.add_handler(CommandHandler("banall", ban_all_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    if WEBHOOK_URL:
        # Best for hosts that require the app to serve HTTP on a given PORT
        # (e.g. Render/Railway web services). Binds directly, no extra server.
        print(f"Bot starting in webhook mode on port {PORT}...")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL.rstrip('/')}/{TELEGRAM_BOT_TOKEN}",
        )
    else:
        if ENABLE_KEEPALIVE:
            from keep_alive import keep_alive

            keep_alive()
        print("Bot starting in polling mode... press Ctrl+C to stop.")
        app.run_polling()


if __name__ == "__main__":
    main()
