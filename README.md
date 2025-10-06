# Wordle Tracker Bot - PostgreSQL Version

A Discord bot that automatically tracks Wordle scores from group chat messages and provides comprehensive statistics and analytics.

## Features

### 🎯 **Automatic Score Tracking**
- Monitors group chat for Wordle bot messages
- Automatically parses messages like: `"Your group is on a 20 day streak! 🔥 Here are yesterday's results: 👑 3/6: @bela 4/6: @diego @lily 5/6: @JoshK318 @NICO"`
- Extracts each user's score, date, and winner status (crown emoji)

### 📊 **Statistical Analysis**
- **User Statistics**: Tracks cumulative performance, average scores, win rates
- **Daily Analysis**: Shows daily breakdowns and statistics
- **Relative Performance**: Compares users against daily averages and personal averages
- **Trend Analysis**: Shows recent performance trends with indicators

### 🤖 **Discord Commands**
- `!stats` - Overall leaderboard or specific user stats
- `!stats [username]` - Specific user statistics
- `!daily [date]` - Daily game results and statistics (defaults to yesterday)
- `!relative [date]` - Performance relative to averages
- `!recent [days]` - Recent performance trends (defaults to 7 days)
- `!ping` - Test bot connectivity

### 💾 **PostgreSQL Data Storage**
- Stores data in PostgreSQL database tables
- Scalable and reliable data persistence
- Multi-server support with guild separation
- Automatic database initialization

## Database Schema

### `wordle_scores` Table
```sql
CREATE TABLE wordle_scores (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    username TEXT NOT NULL,
    score INTEGER NOT NULL,
    date DATE NOT NULL,
    is_winner BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, username, date)
);
```

### `user_stats` Table
```sql
CREATE TABLE user_stats (
    guild_id TEXT NOT NULL,
    username TEXT NOT NULL,
    total_score INTEGER DEFAULT 0,
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, username)
);
```

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- PostgreSQL database
- Discord bot token

### 2. Environment Variables
Set the following environment variables:

```bash
# Required
DATABASE_URL=postgresql://username:password@host:port/database_name
BOT_TOKEN=your_discord_bot_token_here
```

### 3. Install Dependencies
```bash
pip install discord.py psycopg2-binary
```

### 4. Configuration
Edit `config.json`:
```json
{
  "command_prefix": "!",
  "settings": {
    "max_recent_days": 30,
    "default_recent_days": 7,
    "auto_save": true
  }
}
```

### 5. Database Setup
The bot will automatically create the required tables when it starts. Make sure your PostgreSQL database exists and is accessible.

### 6. Run the Bot
```bash
python Wordle_Tracker.py
```

## Usage Examples

### Daily Tracking
When a Wordle bot posts daily results, the tracker will automatically:
1. Parse the message and extract scores
2. Store scores with dates and winner information
3. Update cumulative statistics for each player
4. Confirm tracking with a message

### Statistics Commands
- `!stats` → Shows leaderboard with averages and win rates
- `!stats bela` → Shows bela's personal statistics
- `!daily` → Shows yesterday's results and breakdown
- `!relative` → Shows who performed above/below average
- `!recent 14` → Shows 14-day performance trends

## Features

### Multi-Server Support
- Each Discord server (guild) has separate data
- Prevents cross-contamination between different groups
- Scales to multiple servers

### Data Integrity
- Unique constraints prevent duplicate entries
- Automatic conflict resolution with upserts
- Transaction-based operations for consistency

### Performance
- Indexed queries for fast data retrieval
- Efficient aggregation queries
- Minimal database connections

## Troubleshooting

### Database Connection Issues
1. Verify `DATABASE_URL` environment variable is set correctly
2. Ensure PostgreSQL server is running and accessible
3. Check database credentials and permissions

### Bot Permission Issues
1. Ensure bot has necessary Discord permissions:
   - Read Messages
   - Send Messages
   - Use Slash Commands
   - Add Reactions

### Message Parsing Issues
1. Check that Wordle bot messages match expected format
2. Verify crown emoji (👑) is used for winners
3. Ensure usernames use @ mentions

## Development

### Testing Message Parser
```python
# Test the message parsing functionality
python test_parser.py
```

### Database Queries
The bot uses parameterized queries to prevent SQL injection and ensure data safety.

### Extending Functionality
- Add new statistics by creating new database queries
- Extend message parsing for different Wordle bot formats
- Add new Discord commands in the command functions

## License

MIT License - Feel free to modify and distribute.