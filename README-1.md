# Telegram Alarm Bot

A personal alarm and reminder bot that lives inside Telegram. Instead of using your phone's built-in clock app, this bot lets you set alarms and reminders through a simple chat interface — accessible from any device where you have Telegram installed.

## What It Does

The bot listens for commands you send it in Telegram and schedules alarms based on your instructions. When an alarm goes off, it sends you a message in the chat. All alarms are saved automatically, so they survive even if the bot is restarted.

## Features

**One-Time Alarms**
Set an alarm for a specific date and time. The bot fires once and removes it automatically — no cleanup needed.

**Recurring Alarms**
Set alarms that repeat on a schedule — every few minutes, every few hours, every day at a set time, or every week on a specific day. These keep running until you cancel them.

**Timezone Support**
Tell the bot your timezone once and all your alarms respect your local time, regardless of where the bot is hosted.

**Alarm Management**
View a list of all your active alarms at any time and cancel any of them individually by their ID.

**Persistent Storage**
Alarms are saved to a local file. If the bot ever restarts, all scheduled alarms are automatically restored and continue running as normal.

## Commands

| Command | What it does |
|---|---|
| `/settimezone` | Set your local timezone |
| `/alarm` | Set a one-time alarm |
| `/repeat` | Set a recurring alarm (minutely, hourly, daily, weekly) |
| `/list` | View all your active alarms |
| `/cancel` | Cancel an alarm by its ID |
| `/help` | Show full usage instructions with examples |
