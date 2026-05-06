#!/usr/bin/env python3
"""
Telegram Alarm Bot
------------------
Features:
  - One-time alarms
  - Recurring alarms: minutely, hourly, daily, weekly
  - List & cancel alarms
  - Per-user timezone support
  - Persistent storage (alarms.json)

Commands:
  /start           - Welcome message
  /help            - Show all commands
  /settimezone     - Set your timezone (e.g. /settimezone Europe/London)
  /alarm           - One-time alarm  (e.g. /alarm 2026-05-07 14:30 Meeting!)
  /repeat          - Recurring alarm (e.g. /repeat daily 07:00 Good morning!)
  /list            - List all your active alarms
  /cancel <id>     - Cancel an alarm by ID

Dependencies:
  pip install python-telegram-bot==20.* apscheduler pytz
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DATA_FILE = "alarms.json"
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

# ── Persistent storage ────────────────────────────────────────────────────────

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"alarms": {}, "timezones": {}}


def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


data = load_data()

# ── Scheduler ─────────────────────────────────────────────────────────────────
scheduler = AsyncIOScheduler()


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_tz(chat_id: int) -> pytz.BaseTzInfo:
    tz_name = data["timezones"].get(str(chat_id), "UTC")
    return pytz.timezone(tz_name)


def store_alarm(chat_id: int, alarm_id: str, kind: str, label: str, details: dict):
    data["alarms"][alarm_id] = {
        "chat_id": chat_id,
        "kind": kind,
        "label": label,
        "details": details,
        "created": datetime.utcnow().isoformat(),
    }
    save_data(data)


def remove_alarm(alarm_id: str):
    data["alarms"].pop(alarm_id, None)
    save_data(data)
    try:
        scheduler.remove_job(alarm_id)
    except Exception:
        pass


async def fire_alarm(app: Application, chat_id: int, alarm_id: str, label: str, recurring: bool):
    try:
        await app.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ *Alarm!*\n{label}\n\n`ID: {alarm_id}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        log.error(f"Failed to send alarm {alarm_id}: {e}")
    if not recurring:
        remove_alarm(alarm_id)


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to Alarm Bot!*\n\nType /help to see all commands.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🕐 *Alarm Bot — Commands*\n\n"
        "*Set your timezone first:*\n"
        "`/settimezone America/New_York`\n"
        "`/settimezone Europe/London`\n"
        "`/settimezone Asia/Kolkata`\n\n"
        "*One-time alarm:*\n"
        "`/alarm YYYY-MM-DD HH:MM Your message`\n"
        "Example: `/alarm 2026-05-07 09:00 Morning meeting`\n\n"
        "*Recurring alarm:*\n"
        "`/repeat <frequency> <time or interval> <message>`\n\n"
        "  Frequencies:\n"
        "  • `minutely <N>` — every N minutes\n"
        "    e.g. `/repeat minutely 30 Drink water`\n"
        "  • `hourly <N>` — every N hours\n"
        "    e.g. `/repeat hourly 2 Check email`\n"
        "  • `daily HH:MM` — every day at time\n"
        "    e.g. `/repeat daily 07:30 Good morning!`\n"
        "  • `weekly MON HH:MM` — every week on a day\n"
        "    e.g. `/repeat weekly MON 09:00 Team standup`\n\n"
        "*Manage alarms:*\n"
        "`/list` — show your active alarms\n"
        "`/cancel <id>` — cancel an alarm\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cmd_settimezone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Usage: `/settimezone America/New_York`\n"
            "Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
            parse_mode="Markdown",
        )
        return
    tz_name = args[0].strip()
    try:
        pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        await update.message.reply_text(f"❌ Unknown timezone: `{tz_name}`", parse_mode="Markdown")
        return
    data["timezones"][str(chat_id)] = tz_name
    save_data(data)
    await update.message.reply_text(f"✅ Timezone set to `{tz_name}`", parse_mode="Markdown")


async def cmd_alarm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """One-time alarm: /alarm YYYY-MM-DD HH:MM Message"""
    chat_id = update.effective_chat.id
    args = ctx.args
    if len(args) < 3:
        await update.message.reply_text(
            "Usage: `/alarm YYYY-MM-DD HH:MM Your message`", parse_mode="Markdown"
        )
        return

    date_str, time_str = args[0], args[1]
    label = " ".join(args[2:])
    tz = get_tz(chat_id)

    try:
        naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        local_dt = tz.localize(naive_dt)
    except ValueError:
        await update.message.reply_text("❌ Invalid date/time format. Use `YYYY-MM-DD HH:MM`", parse_mode="Markdown")
        return

    if local_dt < datetime.now(tz):
        await update.message.reply_text("❌ That time is in the past!")
        return

    alarm_id = str(uuid.uuid4())[:8]
    app = ctx.application

    scheduler.add_job(
        fire_alarm,
        trigger=DateTrigger(run_date=local_dt),
        args=[app, chat_id, alarm_id, label, False],
        id=alarm_id,
    )
    store_alarm(chat_id, alarm_id, "once", label, {"datetime": local_dt.isoformat()})

    await update.message.reply_text(
        f"✅ *One-time alarm set!*\n"
        f"🕐 {local_dt.strftime('%Y-%m-%d %H:%M')} ({tz.zone})\n"
        f"📝 {label}\n"
        f"🆔 `{alarm_id}`",
        parse_mode="Markdown",
    )


async def cmd_repeat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Recurring alarm:
      /repeat minutely 30 Message
      /repeat hourly 2 Message
      /repeat daily 07:00 Message
      /repeat weekly MON 09:00 Message
    """
    chat_id = update.effective_chat.id
    args = ctx.args
    tz = get_tz(chat_id)
    app = ctx.application

    if len(args) < 3:
        await update.message.reply_text("Usage: `/repeat daily 07:00 Message`", parse_mode="Markdown")
        return

    freq = args[0].lower()
    alarm_id = str(uuid.uuid4())[:8]

    try:
        if freq == "minutely":
            n = int(args[1])
            label = " ".join(args[2:])
            trigger = IntervalTrigger(minutes=n, timezone=tz)
            detail = f"Every {n} minute(s)"

        elif freq == "hourly":
            n = int(args[1])
            label = " ".join(args[2:])
            trigger = IntervalTrigger(hours=n, timezone=tz)
            detail = f"Every {n} hour(s)"

        elif freq == "daily":
            t = datetime.strptime(args[1], "%H:%M")
            label = " ".join(args[2:])
            trigger = CronTrigger(hour=t.hour, minute=t.minute, timezone=tz)
            detail = f"Daily at {args[1]} ({tz.zone})"

        elif freq == "weekly":
            if len(args) < 4:
                raise ValueError("Need day and time")
            day_map = {
                "MON": "mon", "TUE": "tue", "WED": "wed", "THU": "thu",
                "FRI": "fri", "SAT": "sat", "SUN": "sun",
            }
            day = args[1].upper()
            if day not in day_map:
                await update.message.reply_text("❌ Day must be MON TUE WED THU FRI SAT SUN")
                return
            t = datetime.strptime(args[2], "%H:%M")
            label = " ".join(args[3:])
            trigger = CronTrigger(day_of_week=day_map[day], hour=t.hour, minute=t.minute, timezone=tz)
            detail = f"Every {day} at {args[2]} ({tz.zone})"

        else:
            await update.message.reply_text("❌ Frequency must be: `minutely`, `hourly`, `daily`, or `weekly`", parse_mode="Markdown")
            return

    except (ValueError, IndexError) as e:
        await update.message.reply_text(f"❌ Invalid arguments: {e}\nType /help for usage.", parse_mode="Markdown")
        return

    scheduler.add_job(
        fire_alarm,
        trigger=trigger,
        args=[app, chat_id, alarm_id, label, True],
        id=alarm_id,
    )
    store_alarm(chat_id, alarm_id, freq, label, {"detail": detail})

    await update.message.reply_text(
        f"✅ *Recurring alarm set!*\n"
        f"🔁 {detail}\n"
        f"📝 {label}\n"
        f"🆔 `{alarm_id}`",
        parse_mode="Markdown",
    )


async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_alarms = {
        aid: a for aid, a in data["alarms"].items()
        if a["chat_id"] == chat_id
    }
    if not user_alarms:
        await update.message.reply_text("📭 You have no active alarms. Use /alarm or /repeat to set one.")
        return

    lines = ["⏰ *Your active alarms:*\n"]
    for aid, a in user_alarms.items():
        kind = a["kind"]
        label = a["label"]
        detail = a["details"].get("detail") or a["details"].get("datetime", "")
        emoji = "🔂" if kind not in ("once",) else "1️⃣"
        lines.append(f"{emoji} `{aid}` — *{kind}*\n   📝 {label}\n   🕐 {detail}\n")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = ctx.args
    if not args:
        await update.message.reply_text("Usage: `/cancel <alarm_id>`", parse_mode="Markdown")
        return
    alarm_id = args[0].strip()
    alarm = data["alarms"].get(alarm_id)
    if not alarm or alarm["chat_id"] != chat_id:
        await update.message.reply_text(f"❌ Alarm `{alarm_id}` not found.", parse_mode="Markdown")
        return
    remove_alarm(alarm_id)
    await update.message.reply_text(f"🗑️ Alarm `{alarm_id}` cancelled.", parse_mode="Markdown")


# ── Restore alarms on startup ─────────────────────────────────────────────────

def restore_alarms(app: Application):
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    to_remove = []

    for alarm_id, alarm in data["alarms"].items():
        chat_id = alarm["chat_id"]
        label = alarm["label"]
        kind = alarm["kind"]
        details = alarm["details"]

        try:
            tz = pytz.timezone(data["timezones"].get(str(chat_id), "UTC"))

            if kind == "once":
                dt = datetime.fromisoformat(details["datetime"])
                if isinstance(dt, datetime) and dt.tzinfo is None:
                    dt = pytz.utc.localize(dt)
                if dt < now:
                    to_remove.append(alarm_id)
                    continue
                scheduler.add_job(
                    fire_alarm,
                    trigger=DateTrigger(run_date=dt),
                    args=[app, chat_id, alarm_id, label, False],
                    id=alarm_id,
                )

            elif kind == "minutely":
                n = int(details.get("detail", "every 1 minute(s)").split()[1])
                scheduler.add_job(
                    fire_alarm,
                    trigger=IntervalTrigger(minutes=n, timezone=tz),
                    args=[app, chat_id, alarm_id, label, True],
                    id=alarm_id,
                )

            elif kind == "hourly":
                n = int(details.get("detail", "every 1 hour(s)").split()[1])
                scheduler.add_job(
                    fire_alarm,
                    trigger=IntervalTrigger(hours=n, timezone=tz),
                    args=[app, chat_id, alarm_id, label, True],
                    id=alarm_id,
                )

            elif kind == "daily":
                detail = details.get("detail", "")
                time_str = detail.split("at")[1].split("(")[0].strip()
                t = datetime.strptime(time_str, "%H:%M")
                scheduler.add_job(
                    fire_alarm,
                    trigger=CronTrigger(hour=t.hour, minute=t.minute, timezone=tz),
                    args=[app, chat_id, alarm_id, label, True],
                    id=alarm_id,
                )

            elif kind == "weekly":
                detail = details.get("detail", "")
                day_map = {"MON":"mon","TUE":"tue","WED":"wed","THU":"thu","FRI":"fri","SAT":"sat","SUN":"sun"}
                parts = detail.split()
                day = day_map.get(parts[1].upper(), "mon")
                time_str = parts[3]
                t = datetime.strptime(time_str, "%H:%M")
                scheduler.add_job(
                    fire_alarm,
                    trigger=CronTrigger(day_of_week=day, hour=t.hour, minute=t.minute, timezone=tz),
                    args=[app, chat_id, alarm_id, label, True],
                    id=alarm_id,
                )

        except Exception as e:
            log.warning(f"Could not restore alarm {alarm_id}: {e}")
            to_remove.append(alarm_id)

    for aid in to_remove:
        data["alarms"].pop(aid, None)
    if to_remove:
        save_data(data)

    log.info(f"Restored {len(data['alarms'])} alarm(s).")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Set your bot token via the TELEGRAM_BOT_TOKEN environment variable.")
        print("  export TELEGRAM_BOT_TOKEN='123456:ABC-...'")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("settimezone", cmd_settimezone))
    app.add_handler(CommandHandler("alarm", cmd_alarm))
    app.add_handler(CommandHandler("repeat", cmd_repeat))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    scheduler.start()
    restore_alarms(app)

    log.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
