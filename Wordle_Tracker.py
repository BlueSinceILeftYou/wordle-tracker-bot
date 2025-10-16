from discord.ext import commands
import discord
from dataclasses import dataclass
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    """Get a connection to the PostgreSQL database"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def init_db():
    """Initialize the database tables"""
    conn = get_connection()
    cur = conn.cursor()

    # Create wordle_scores table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS wordle_scores (
        id SERIAL PRIMARY KEY,
        guild_id TEXT NOT NULL,
        username TEXT NOT NULL,
        score INTEGER NOT NULL,
        date DATE NOT NULL,
        is_winner BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(guild_id, username, date)
    )
    """)

    # Create user_stats table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_stats (
        guild_id TEXT NOT NULL,
        username TEXT NOT NULL,
        total_score INTEGER DEFAULT 0,
        games_played INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (guild_id, username)
    )
    """)

    # Create indexes for better performance
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_wordle_scores_guild_date 
    ON wordle_scores(guild_id, date)
    """)
    
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_wordle_scores_guild_user 
    ON wordle_scores(guild_id, username)
    """)

    conn.commit()
    conn.close()


Bot_Token = os.getenv("bot_token")


# Load configuration
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
        Channel_ID = config["channel_id"]
        COMMAND_PREFIX = config["command_prefix"]
        DATA_FILES = config["data_files"]
        SETTINGS = config["settings"]

    # Load bot token from environment variable
    Bot_Token = os.getenv("BOT_TOKEN")
    if not Bot_Token:
        raise ValueError("❌ BOT_TOKEN environment variable not set!")
except FileNotFoundError:
    # Fallback to hardcoded values if config file doesn't exist
    COMMAND_PREFIX = "!"
    DATA_FILES = {"wordle_data": "wordle_data.json", "user_stats": "user_stats.json"}
    SETTINGS = {"max_recent_days": 30, "default_recent_days": 7, "auto_save": True}

@dataclass
class WordleScore:
    user: str
    score: int
    date: str
    is_winner: bool = False

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=discord.Intents.all())

def save_wordle_scores(guild_id: str, scores: List[WordleScore]):
    """Save Wordle scores to the database"""
    conn = get_connection()
    cur = conn.cursor()
    
    for score in scores:
        try:
            cur.execute("""
                INSERT INTO wordle_scores (guild_id, username, score, date, is_winner)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (guild_id, username, date) 
                DO UPDATE SET 
                    score = EXCLUDED.score,
                    is_winner = EXCLUDED.is_winner,
                    created_at = CURRENT_TIMESTAMP
            """, (guild_id, score.user, score.score, score.date, score.is_winner))
        except Exception as e:
            print(f"Error saving score for {score.user}: {e}")
    
    conn.commit()
    conn.close()

def update_user_stats(guild_id: str, scores: List[WordleScore]):
    """Update cumulative user statistics in the database"""
    conn = get_connection()
    cur = conn.cursor()
    
    for score in scores:
        try:
            # Insert or update user stats
            cur.execute("""
                INSERT INTO user_stats (guild_id, username, total_score, games_played, wins)
                VALUES (%s, %s, %s, 1, %s)
                ON CONFLICT (guild_id, username)
                DO UPDATE SET
                    total_score = user_stats.total_score + %s,
                    games_played = user_stats.games_played + 1,
                    wins = user_stats.wins + %s,
                    last_updated = CURRENT_TIMESTAMP
            """, (guild_id, score.user, score.score, 1 if score.is_winner else 0, 
                  score.score, 1 if score.is_winner else 0))
        except Exception as e:
            print(f"Error updating stats for {score.user}: {e}")
    
    conn.commit()
    conn.close()

def resolve_username_to_user_id(bot, guild, username: str) -> str:
    """
    Resolve a username to a Discord user ID. Try multiple resolution strategies.
    Returns the user ID as a string, or f"unresolved_{username}" if resolution fails.
    """
    if not guild:
        return f"unresolved_{username}"
    
    username_lower = username.lower()
    
    # Try to find the user by display name, username, or global name
    for member in guild.members:
        if (member.display_name.lower() == username_lower or 
            member.name.lower() == username_lower or
            (member.global_name and member.global_name.lower() == username_lower)):
            return str(member.id)
    
    # Try partial matching (in case of nickname changes)
    for member in guild.members:
        if (username_lower in member.display_name.lower() or
            username_lower in member.name.lower() or
            (member.global_name and username_lower in member.global_name.lower())):
            return str(member.id)
    
    # If all resolution attempts fail, store as unresolved
    return f"unresolved_{username}"

def resolve_pending_usernames(guild):
    """
    Attempt to resolve any 'unresolved_' usernames in the database to actual user IDs.
    Call this periodically or when new members join to clean up old unresolved entries.
    """
    if not guild:
        return
    
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Find all unresolved usernames in the database
    cur.execute("""
        SELECT DISTINCT username FROM wordle_scores 
        WHERE guild_id = %s AND username LIKE 'unresolved_%'
        UNION
        SELECT DISTINCT username FROM user_stats 
        WHERE guild_id = %s AND username LIKE 'unresolved_%'
    """, (str(guild.id), str(guild.id)))
    
    unresolved_entries = cur.fetchall()
    
    for entry in unresolved_entries:
        old_username = entry['username']
        actual_username = old_username.replace('unresolved_', '')
        
        # Try to resolve to actual user ID
        new_user_id = resolve_username_to_user_id(None, guild, actual_username)
        
        # If we successfully resolved it and it's not still unresolved
        if not new_user_id.startswith('unresolved_'):
            # Update wordle_scores table
            cur.execute("""
                UPDATE wordle_scores 
                SET username = %s 
                WHERE guild_id = %s AND username = %s
            """, (new_user_id, str(guild.id), old_username))
            
            # Update user_stats table  
            cur.execute("""
                UPDATE user_stats 
                SET username = %s 
                WHERE guild_id = %s AND username = %s
            """, (new_user_id, str(guild.id), old_username))
    
    conn.commit()
    conn.close()

def get_user_display_name(bot, guild_id: str, user_id: str) -> str:
    """Get a user's display name from their ID"""
    if user_id.startswith("unresolved_"):
        return user_id.replace("unresolved_", "")
    
    try:
        guild = bot.get_guild(int(guild_id)) if guild_id != "DM" else None
        if guild:
            member = guild.get_member(int(user_id))
            if member:
                return member.display_name or member.name
        else:
            # Try to get user from cache
            user = bot.get_user(int(user_id))
            if user:
                return user.display_name or user.name
    except (ValueError, AttributeError):
        pass
    
    return f"User#{user_id}"

def get_user_stats(guild_id: str, username: str = None) -> Dict:
    """Get user statistics from the database"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if username:
        cur.execute("""
            SELECT * FROM user_stats 
            WHERE guild_id = %s AND username = %s
        """, (guild_id, username))
        result = cur.fetchone()
        conn.close()
        return dict(result) if result else {}
    else:
        cur.execute("""
            SELECT * FROM user_stats 
            WHERE guild_id = %s
            ORDER BY (total_score::float / GREATEST(games_played, 1)) ASC
        """, (guild_id,))
        results = cur.fetchall()
        conn.close()
        return [dict(row) for row in results]

def get_user_average(guild_id: str, username: str) -> float:
    """Get a user's average score from the database"""
    stats = get_user_stats(guild_id, username)
    if not stats or stats.get("games_played", 0) == 0:
        return 0.0
    return stats["total_score"] / stats["games_played"]

def get_daily_scores(guild_id: str, date: str) -> List[WordleScore]:
    """Get all scores for a specific date from the database"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT username, score, date, is_winner
        FROM wordle_scores 
        WHERE guild_id = %s AND date = %s
        ORDER BY score ASC, username ASC
    """, (guild_id, date))
    
    results = cur.fetchall()
    conn.close()
    
    return [WordleScore(
        user=row['username'],
        score=row['score'],
        date=str(row['date']),
        is_winner=row['is_winner']
    ) for row in results]

def get_daily_stats(guild_id: str, date: str) -> Dict:
    """Get statistics for a specific date from the database"""
    scores = get_daily_scores(guild_id, date)
    
    if not scores:
        return {}
    
    score_values = [s.score for s in scores]
    
    return {
        "average": sum(score_values) / len(score_values),
        "median": sorted(score_values)[len(score_values) // 2],
        "best_score": min(score_values),
        "worst_score": max(score_values),
        "total_players": len(scores)
    }

def get_recent_dates(guild_id: str, days: int) -> List[str]:
    """Get dates that have data within the specified number of days"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT date
        FROM wordle_scores 
        WHERE guild_id = %s 
        AND date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY date DESC
    """, (guild_id, days))
    
    results = cur.fetchall()
    conn.close()
    
    return [str(row[0]) for row in results]


def parse_wordle_message(message_content: str, guild=None) -> Optional[List[WordleScore]]:
    """Parse the Wordle bot message and extract scores"""
    # Pattern to match the streak message
    streak_pattern = r"Your group is on a (\d+) day streak!"
    
    if not re.search(streak_pattern, message_content):
        return None
    
    # Extract scores using pattern matching
    # Looking for patterns like "👑 3/6: @user1" or "4/6: @user1 @user2"
    score_pattern = r"(👑\s*)?(\d+)/6:\s*(.+)"
    
    scores = []
    lines = message_content.split('\n')
    
    for line in lines:
        match = re.search(score_pattern, line)
        if match:
            is_winner = match.group(1) is not None  # Crown emoji indicates winner
            score = int(match.group(2))
            users_text = match.group(3).strip()
            
            # Extract both Discord user mentions and plain @username mentions
            # Discord mentions: <@user_id> or <@!user_id>
            discord_mentions = re.findall(r'<@!?(\d+)>', users_text)
            # Plain mentions: @username (for cases where ping failed)
            plain_mentions = re.findall(r'@(\w+)', users_text)
            
            # Process Discord mentions 
            for user_id in discord_mentions:
                scores.append(WordleScore(
                    user=user_id,  # Store the actual Discord user ID
                    score=score,
                    date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                    is_winner=is_winner
                ))
            
            # Process plain mentions (try to resolve to user IDs if possible)
            for username in plain_mentions:
                # Skip if we already found this as a Discord mention
                if f"@{username}" not in users_text.replace(f"<@", "DISCORD_MENTION"):
                    # Use the new resolution function
                    user_id = resolve_username_to_user_id(bot, guild, username)
                    scores.append(WordleScore(
                        user=user_id,
                        score=score,
                        date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                        is_winner=is_winner
                    ))
    
    return scores if scores else None


@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and ready!")
    init_db()  # Initialize database when bot starts

@bot.event
async def on_member_join(member):
    """When a new member joins, try to resolve any pending unresolved usernames"""
    resolve_pending_usernames(member.guild)

@bot.command()
async def ping(ctx):
    await ctx.send("✅ I'm online and ready to track Wordle scores!")

@bot.command()
async def botinfo(ctx):
    """Show information about bots in the server (for debugging)"""
    if not ctx.guild:
        await ctx.send("This command only works in servers!")
        return
    
    bots = [member for member in ctx.guild.members if member.bot]
    
    embed = discord.Embed(title="🤖 Bots in this server", color=0x0099ff)
    
    for bot_member in bots[:10]:  # Limit to 10 bots
        bot_info = f"ID: {bot_member.id}\nName: {bot_member.name}\nFull: {str(bot_member)}"
        embed.add_field(name=f"{bot_member.display_name}", value=bot_info, inline=True)
    
    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    # Don't respond to our own messages
    if message.author == bot.user:
        return
    
    # Only respond to messages from the specific Wordle bot (Wordle #2092)
    if (message.author.id == 1211781489931452447): 
        # Check if this is a Wordle streak message
        if "Your group is on a" in message.content and "day streak!" in message.content:
            scores = parse_wordle_message(message.content, message.guild)
            if scores:
                guild_id = str(message.guild.id) if message.guild else "DM"
                
                # Save scores and update stats
                save_wordle_scores(guild_id, scores)
                update_user_stats(guild_id, scores)
                
                # Send confirmation message
                date = scores[0].date  # All scores will have the same date
                await message.add_reaction("✅")
                await message.channel.send(f"📊 Recorded {len(scores)} Wordle scores for {date}!")
    
    # Process other commands
    await bot.process_commands(message)



@bot.command()
async def stats(ctx, user: str = None):
    """Show user statistics"""
    guild_id = str(ctx.guild.id) if ctx.guild else "DM"
    
    if user is None:
        # Show overall statistics
        embed = discord.Embed(title="📊 Overall Wordle Statistics", color=0x00ff00)
        
        all_stats = get_user_stats(guild_id)
        if not all_stats:
            embed.add_field(name="No Data", value="No Wordle scores recorded yet!", inline=False)
        else:
            leaderboard = ""
            for i, stats in enumerate(all_stats[:10], 1):
                user_id = stats["username"]
                display_name = get_user_display_name(bot, guild_id, user_id)
                avg = stats["total_score"] / stats["games_played"] if stats["games_played"] > 0 else 0
                win_rate = (stats["wins"] / stats["games_played"] * 100) if stats["games_played"] > 0 else 0
                leaderboard += f"{i}. **{display_name}**: {avg:.2f} avg ({stats['games_played']} games, {win_rate:.1f}% wins)\n"
            
            embed.add_field(name="🏆 Leaderboard (Best Average)", value=leaderboard or "No data", inline=False)
        
        await ctx.send(embed=embed)
    else:
        # Try to resolve user mention to user ID
        resolved_user_id = user
        if user.startswith('<@') and user.endswith('>'):
            # Extract user ID from mention
            resolved_user_id = user.strip('<@!>')
        else:
            # Try to find user by display name
            if ctx.guild:
                for member in ctx.guild.members:
                    if (member.display_name.lower() == user.lower() or 
                        member.name.lower() == user.lower() or
                        (member.global_name and member.global_name.lower() == user.lower())):
                        resolved_user_id = str(member.id)
                        break
        
        # Show specific user statistics
        stats_data = get_user_stats(guild_id, resolved_user_id)
        if not stats_data:
            await ctx.send(f"No data found for user: {user}")
            return
        
        display_name = get_user_display_name(bot, guild_id, resolved_user_id)
        avg = stats_data["total_score"] / stats_data["games_played"] if stats_data["games_played"] > 0 else 0
        win_rate = (stats_data["wins"] / stats_data["games_played"] * 100) if stats_data["games_played"] > 0 else 0
        
        embed = discord.Embed(title=f"📊 {display_name}'s Wordle Statistics", color=0x00ff00)
        embed.add_field(name="Games Played", value=stats_data["games_played"], inline=True)
        embed.add_field(name="Average Score", value=f"{avg:.2f}", inline=True)
        embed.add_field(name="Win Rate", value=f"{win_rate:.1f}%", inline=True)
        embed.add_field(name="Total Wins", value=stats_data["wins"], inline=True)
        
        await ctx.send(embed=embed)

@bot.command()
async def daily(ctx, date: str = None):
    """Show daily statistics"""
    guild_id = str(ctx.guild.id) if ctx.guild else "DM"
    
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    scores = get_daily_scores(guild_id, date)
    if not scores:
        await ctx.send(f"No data found for {date}")
        return
    
    daily_stats = get_daily_stats(guild_id, date)
    
    embed = discord.Embed(title=f"📅 Daily Stats for {date}", color=0x0099ff)
    embed.add_field(name="Players", value=daily_stats["total_players"], inline=True)
    embed.add_field(name="Average Score", value=f"{daily_stats['average']:.2f}", inline=True)
    embed.add_field(name="Best Score", value=daily_stats["best_score"], inline=True)
    
    # Show individual scores with display names
    score_breakdown = {}
    for score in scores:
        if score.score not in score_breakdown:
            score_breakdown[score.score] = []
        display_name = get_user_display_name(bot, guild_id, score.user)
        score_breakdown[score.score].append(display_name)
    
    breakdown_text = ""
    for score in sorted(score_breakdown.keys()):
        users = score_breakdown[score]
        crown = "👑 " if any(s.is_winner for s in scores if s.score == score) else ""
        breakdown_text += f"{crown}{score}/6: {', '.join(users)}\n"
    
    embed.add_field(name="Score Breakdown", value=breakdown_text or "No scores", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def relative(ctx, date: str = None):
    """Show how users performed relative to the daily average"""
    guild_id = str(ctx.guild.id) if ctx.guild else "DM"
    
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    scores = get_daily_scores(guild_id, date)
    if not scores:
        await ctx.send(f"No data found for {date}")
        return
    
    daily_stats = get_daily_stats(guild_id, date)
    daily_avg = daily_stats["average"]
    
    embed = discord.Embed(title=f"📈 Relative Performance for {date}", color=0xff9900)
    embed.add_field(name="Daily Average", value=f"{daily_avg:.2f}", inline=False)
    
    # Calculate relative performance
    relative_scores = []
    for score in scores:
        user_avg = get_user_average(guild_id, score.user)
        relative_to_daily = score.score - daily_avg
        relative_to_personal = score.score - user_avg
        display_name = get_user_display_name(bot, guild_id, score.user)
        relative_scores.append((display_name, score.score, relative_to_daily, relative_to_personal))
    
    # Sort by performance relative to daily average
    relative_scores.sort(key=lambda x: x[2])
    
    performance_text = ""
    for display_name, score, rel_daily, rel_personal in relative_scores:
        daily_indicator = "📈" if rel_daily > 0 else "📉" if rel_daily < 0 else "➡️"
        personal_indicator = "📈" if rel_personal > 0 else "📉" if rel_personal < 0 else "➡️"
        performance_text += f"**{display_name}**: {score}/6 {daily_indicator} {rel_daily:+.2f} vs daily, {personal_indicator} {rel_personal:+.2f} vs personal avg\n"
    
    embed.add_field(name="Performance Analysis", value=performance_text or "No data", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def recent(ctx, days: int = None):
    """Show recent performance trends"""
    guild_id = str(ctx.guild.id) if ctx.guild else "DM"
    
    if days is None:
        days = SETTINGS["default_recent_days"]
    if days > SETTINGS["max_recent_days"]:
        days = SETTINGS["max_recent_days"]
    
    recent_dates = get_recent_dates(guild_id, days)
    
    if not recent_dates:
        await ctx.send(f"No data found for the last {days} days")
        return
    
    embed = discord.Embed(title=f"📊 Recent Performance ({len(recent_dates)} days)", color=0x9932cc)
    
    # Calculate trends for each user
    user_trends = {}
    for date in recent_dates:
        scores = get_daily_scores(guild_id, date)
        for score in scores:
            if score.user not in user_trends:
                user_trends[score.user] = []
            user_trends[score.user].append(score.score)
    
    trend_text = ""
    for user_id, scores in user_trends.items():
        if len(scores) >= 2:
            recent_avg = sum(scores[-3:]) / len(scores[-3:])  # Last 3 games
            overall_avg = sum(scores) / len(scores)
            trend = "📈" if recent_avg > overall_avg else "📉" if recent_avg < overall_avg else "➡️"
            display_name = get_user_display_name(bot, guild_id, user_id)
            trend_text += f"**{display_name}**: {len(scores)} games, recent avg: {recent_avg:.2f} {trend}\n"
    
    embed.add_field(name="User Trends", value=trend_text or "No trends available", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def cleanup(ctx):
    """Manually resolve any pending unresolved usernames"""
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return
    
    resolve_pending_usernames(ctx.guild)
    await ctx.send("✅ Attempted to resolve any pending unresolved usernames.")

# Only run the bot if this file is executed directly
if __name__ == "__main__":
    init_db()
    bot.run(Bot_Token)