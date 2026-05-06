# Telegram Alarm Bot — Setup Guide

## 1. Get a Bot Token
1. Open Telegram → search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token (looks like `123456789:ABCdef...`)

## 2. Install dependencies
```bash
pip install -r requirements.txt
```

## 3. Set your token & run
```bash
export TELEGRAM_BOT_TOKEN="your_token_here"
python alarm_bot.py
```

Or inline:
```bash
TELEGRAM_BOT_TOKEN="your_token_here" python alarm_bot.py
```

---

## Bot Commands

| Command | Example | Description |
|---|---|---|
| `/settimezone` | `/settimezone America/New_York` | Set your local timezone |
| `/alarm` | `/alarm 2026-05-08 08:00 Morning call` | One-time alarm |
| `/repeat minutely` | `/repeat minutely 15 Stretch break` | Every N minutes |
| `/repeat hourly` | `/repeat hourly 2 Drink water` | Every N hours |
| `/repeat daily` | `/repeat daily 07:00 Good morning!` | Every day at a time |
| `/repeat weekly` | `/repeat weekly MON 09:00 Team standup` | Weekly on a day |
| `/list` | `/list` | Show all active alarms |
| `/cancel` | `/cancel a1b2c3d4` | Cancel by ID |

Days for weekly: `MON TUE WED THU FRI SAT SUN`

---

## Hosting Options

### Option A — Run locally (testing)
Just run the script. Alarms fire while it's running.

### Option B — VPS / cloud server (recommended for 24/7)
Any cheap VPS works (DigitalOcean, Hetzner, AWS EC2 free tier).

Use **systemd** to keep it alive:
```ini
# /etc/systemd/system/alarmbot.service
[Unit]
Description=Telegram Alarm Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/alarm-bot
ExecStart=/usr/bin/python3 /home/ubuntu/alarm-bot/alarm_bot.py
Environment=TELEGRAM_BOT_TOKEN=your_token_here
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable alarmbot
sudo systemctl start alarmbot
sudo systemctl status alarmbot
```

### Option C — Raspberry Pi
Same as Option B. Runs perfectly on a Pi Zero W.

### Option D — Railway / Render (free cloud)
- Push to GitHub
- Connect to [Railway](https://railway.app) or [Render](https://render.com)
- Set `TELEGRAM_BOT_TOKEN` as an environment variable
- Set start command: `python alarm_bot.py`

---

## Data
Alarms are saved to `alarms.json` in the same folder. They survive restarts automatically.
