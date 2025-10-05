from discord.ext import commands
import discord
from dataclasses import dataclass
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics
import os

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

# Data storage
wordle_data = {}  # Will store: {date: [WordleScore objects]}
user_stats = {}   # Will store: {user: {"total_score": int, "games_played": int, "wins": int}}

def load_data():
    """Load existing data from JSON files"""
    global wordle_data, user_stats
    try:
        with open(DATA_FILES["wordle_data"], 'r') as f:
            data = json.load(f)
            wordle_data = {}
            for date, scores in data.items():
                wordle_data[date] = [WordleScore(**score) for score in scores]
    except FileNotFoundError:
        wordle_data = {}
    
    try:
        with open(DATA_FILES["user_stats"], 'r') as f:
            user_stats = json.load(f)
    except FileNotFoundError:
        user_stats = {}

def save_data():
    """Save data to JSON files"""
    if not SETTINGS["auto_save"]:
        return
        
    # Convert WordleScore objects to dictionaries for JSON serialization
    data_to_save = {}
    for date, scores in wordle_data.items():
        data_to_save[date] = [score.__dict__ for score in scores]
    
    with open(DATA_FILES["wordle_data"], 'w') as f:
        json.dump(data_to_save, f, indent=2)
    
    with open(DATA_FILES["user_stats"], 'w') as f:
        json.dump(user_stats, f, indent=2)

def parse_wordle_message(message_content: str) -> Optional[tuple]:
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
            
            # Extract usernames (remove @ symbols)
            users = re.findall(r'@(\w+)', users_text)
            
            for user in users:
                scores.append(WordleScore(
                    user=user,
                    score=score,
                    date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),  # Yesterday's date
                    is_winner=is_winner
                ))
    
    return scores if scores else None

def update_user_stats(scores: List[WordleScore]):
    """Update cumulative user statistics"""
    for score in scores:
        user = score.user
        if user not in user_stats:
            user_stats[user] = {"total_score": 0, "games_played": 0, "wins": 0}
        
        user_stats[user]["total_score"] += score.score
        user_stats[user]["games_played"] += 1
        if score.is_winner:
            user_stats[user]["wins"] += 1

def get_user_average(user: str) -> float:
    """Get a user's average score"""
    if user not in user_stats or user_stats[user]["games_played"] == 0:
        return 0.0
    return user_stats[user]["total_score"] / user_stats[user]["games_played"]

def get_daily_stats(date: str) -> Dict:
    """Get statistics for a specific date"""
    if date not in wordle_data:
        return {}
    
    scores = wordle_data[date]
    score_values = [s.score for s in scores]
    
    return {
        "average": statistics.mean(score_values) if score_values else 0,
        "median": statistics.median(score_values) if score_values else 0,
        "best_score": min(score_values) if score_values else 0,
        "worst_score": max(score_values) if score_values else 0,
        "total_players": len(scores)
    }


@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online and ready!")
    load_data()

@bot.command()
async def ping(ctx):
    await ctx.send("✅ I'm online and ready to track Wordle scores!")

@bot.event
async def on_message(message):
    # Don't respond to our own messages
    if message.author == bot.user:
        return
    
    # Check if this is a Wordle bot message (you may need to adjust this condition)
    # You can check by bot name, user ID, or message content pattern
    if "Your group is on a" in message.content and "day streak!" in message.content:
        scores = parse_wordle_message(message.content)
        if scores:
            date = scores[0].date  # All scores will have the same date
            wordle_data[date] = scores
            update_user_stats(scores)
            save_data()
            
            # Send confirmation message
            await message.channel.send(f"📊 Recorded {len(scores)} Wordle scores for {date}!")
    
    # Process other commands
    await bot.process_commands(message)


@bot.command()
async def stats(ctx, user: str = None):
    """Show user statistics"""
    if user is None:
        # Show overall statistics
        embed = discord.Embed(title="📊 Overall Wordle Statistics", color=0x00ff00)
        
        if not user_stats:
            embed.add_field(name="No Data", value="No Wordle scores recorded yet!", inline=False)
        else:
            # Sort users by average score
            sorted_users = sorted(user_stats.items(), key=lambda x: get_user_average(x[0]))
            
            leaderboard = ""
            for i, (username, stats) in enumerate(sorted_users[:10], 1):
                avg = get_user_average(username)
                win_rate = (stats["wins"] / stats["games_played"] * 100) if stats["games_played"] > 0 else 0
                leaderboard += f"{i}. **{username}**: {avg:.2f} avg ({stats['games_played']} games, {win_rate:.1f}% wins)\n"
            
            embed.add_field(name="🏆 Leaderboard (Best Average)", value=leaderboard or "No data", inline=False)
        
        await ctx.send(embed=embed)
    else:
        # Show specific user statistics
        if user not in user_stats:
            await ctx.send(f"No data found for user: {user}")
            return
        
        stats_data = user_stats[user]
        avg = get_user_average(user)
        win_rate = (stats_data["wins"] / stats_data["games_played"] * 100) if stats_data["games_played"] > 0 else 0
        
        embed = discord.Embed(title=f"📊 {user}'s Wordle Statistics", color=0x00ff00)
        embed.add_field(name="Games Played", value=stats_data["games_played"], inline=True)
        embed.add_field(name="Average Score", value=f"{avg:.2f}", inline=True)
        embed.add_field(name="Win Rate", value=f"{win_rate:.1f}%", inline=True)
        embed.add_field(name="Total Wins", value=stats_data["wins"], inline=True)
        
        await ctx.send(embed=embed)

@bot.command()
async def daily(ctx, date: str = None):
    """Show daily statistics"""
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    if date not in wordle_data:
        await ctx.send(f"No data found for {date}")
        return
    
    daily_stats = get_daily_stats(date)
    scores = wordle_data[date]
    
    embed = discord.Embed(title=f"📅 Daily Stats for {date}", color=0x0099ff)
    embed.add_field(name="Players", value=daily_stats["total_players"], inline=True)
    embed.add_field(name="Average Score", value=f"{daily_stats['average']:.2f}", inline=True)
    embed.add_field(name="Best Score", value=daily_stats["best_score"], inline=True)
    
    # Show individual scores
    score_breakdown = {}
    for score in scores:
        if score.score not in score_breakdown:
            score_breakdown[score.score] = []
        score_breakdown[score.score].append(score.user)
    
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
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    if date not in wordle_data:
        await ctx.send(f"No data found for {date}")
        return
    
    daily_stats = get_daily_stats(date)
    daily_avg = daily_stats["average"]
    scores = wordle_data[date]
    
    embed = discord.Embed(title=f"📈 Relative Performance for {date}", color=0xff9900)
    embed.add_field(name="Daily Average", value=f"{daily_avg:.2f}", inline=False)
    
    # Calculate relative performance
    relative_scores = []
    for score in scores:
        user_avg = get_user_average(score.user)
        relative_to_daily = score.score - daily_avg
        relative_to_personal = score.score - user_avg
        relative_scores.append((score.user, score.score, relative_to_daily, relative_to_personal))
    
    # Sort by performance relative to daily average
    relative_scores.sort(key=lambda x: x[2])
    
    performance_text = ""
    for user, score, rel_daily, rel_personal in relative_scores:
        daily_indicator = "📈" if rel_daily > 0 else "📉" if rel_daily < 0 else "➡️"
        personal_indicator = "📈" if rel_personal > 0 else "📉" if rel_personal < 0 else "➡️"
        performance_text += f"**{user}**: {score}/6 {daily_indicator} {rel_daily:+.2f} vs daily, {personal_indicator} {rel_personal:+.2f} vs personal avg\n"
    
    embed.add_field(name="Performance Analysis", value=performance_text or "No data", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def recent(ctx, days: int = None):
    """Show recent performance trends"""
    if days is None:
        days = SETTINGS["default_recent_days"]
    if days > SETTINGS["max_recent_days"]:
        days = SETTINGS["max_recent_days"]
    
    recent_dates = []
    start_date = datetime.now() - timedelta(days=days)
    
    for i in range(days):
        check_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        if check_date in wordle_data:
            recent_dates.append(check_date)
    
    if not recent_dates:
        await ctx.send(f"No data found for the last {days} days")
        return
    
    embed = discord.Embed(title=f"📊 Recent Performance ({len(recent_dates)} days)", color=0x9932cc)
    
    # Calculate trends for each user
    user_trends = {}
    for date in recent_dates:
        for score in wordle_data[date]:
            if score.user not in user_trends:
                user_trends[score.user] = []
            user_trends[score.user].append(score.score)
    
    trend_text = ""
    for user, scores in user_trends.items():
        if len(scores) >= 2:
            recent_avg = sum(scores[-3:]) / len(scores[-3:])  # Last 3 games
            overall_avg = sum(scores) / len(scores)
            trend = "📈" if recent_avg > overall_avg else "📉" if recent_avg < overall_avg else "➡️"
            trend_text += f"**{user}**: {len(scores)} games, recent avg: {recent_avg:.2f} {trend}\n"
    
    embed.add_field(name="User Trends", value=trend_text or "No trends available", inline=False)
    
    await ctx.send(embed=embed)

# Only run the bot if this file is executed directly
if __name__ == "__main__":
    load_data()  # Load existing data when bot starts
    bot.run(Bot_Token)