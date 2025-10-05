# Wordle Tracker Bot

This Discord bot tracks Wordle scores from a group chat and provides statistics and analytics.

## Features

- **Automatic Score Tracking**: Parses messages from the Wordle bot to extract daily scores
- **User Statistics**: Tracks cumulative performance, averages, and win rates
- **Daily Analysis**: Shows daily statistics and score breakdowns
- **Relative Performance**: Compares users against daily averages and personal averages
- **Trend Analysis**: Shows recent performance trends

## Message Format

The bot recognizes messages in this format:
```
Your group is on a 20 day streak! 🔥 Here are yesterday's results:
👑 3/6: @bela
4/6: @diego @lily
5/6: @JoshK318 @NICO
```

## Commands

### `!stats [user]`
Show overall statistics or specific user statistics
- Without parameter: Shows leaderboard sorted by average score
- With username: Shows detailed stats for that user

### `!daily [date]`
Show daily statistics for a specific date (YYYY-MM-DD format)
- Without parameter: Shows yesterday's stats
- Shows player count, average score, best score, and score breakdown

### `!relative [date]`
Show how users performed relative to the daily average and their personal average
- Without parameter: Shows yesterday's relative performance
- Useful for seeing who over/under-performed

### `!recent [days]`
Show recent performance trends (default: 7 days, max: 30)
- Shows trend indicators (📈📉➡️) comparing recent average to overall average

### `!hello`
Simple test command to verify bot is working

## Setup

1. Install dependencies:
   ```bash
   pip install discord.py
   ```

2. Update the bot token and channel ID in the code:
   ```python
   Bot_Token = "YOUR_BOT_TOKEN_HERE"
   Channel_ID = YOUR_CHANNEL_ID_HERE
   ```

3. Run the bot:
   ```bash
   python Wordle_Tracker.py
   ```

## Data Storage

The bot stores data in two JSON files:
- `wordle_data.json`: Daily scores organized by date
- `user_stats.json`: Cumulative user statistics

These files are automatically created and updated as the bot runs.

## Customization

You can modify the parsing logic in `parse_wordle_message()` if your Wordle bot uses a different message format. The current implementation looks for:
- Streak indicator: "Your group is on a X day streak!"
- Score lines: "👑 3/6: @username" or "4/6: @user1 @user2"
- Crown emoji (👑) indicates the winner(s)

## Example Usage

After the bot processes a daily Wordle message, you can use commands like:

- `!stats` - See the overall leaderboard
- `!stats bela` - See bela's detailed statistics
- `!daily` - See yesterday's game results
- `!relative` - See who performed above/below their average
- `!recent 14` - See 2-week performance trends

## Bot Permissions

The bot needs the following Discord permissions:
- Read Messages
- Send Messages
- Use Slash Commands (if you want to add slash commands later)