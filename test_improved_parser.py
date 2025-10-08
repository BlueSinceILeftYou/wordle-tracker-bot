#!/usr/bin/env python3
"""Test script for the improved Wordle message parser"""

import re
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class MockMember:
    id: int
    name: str
    display_name: str
    global_name: str = None

@dataclass
class WordleScore:
    user: str
    score: int
    date: str
    is_winner: bool = False

def parse_wordle_message(message_content: str, guild_members=None):
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
            
            # Process Discord mentions (these give us actual user IDs)
            for user_id in discord_mentions:
                scores.append(WordleScore(
                    user=user_id,  # Store the actual Discord user ID
                    score=score,
                    date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                    is_winner=is_winner
                ))
            
            # Process plain mentions (try to resolve to user IDs if possible)
            if guild_members:
                for username in plain_mentions:
                    # Skip if we already found this as a Discord mention
                    if f"@{username}" not in users_text.replace(f"<@", "DISCORD_MENTION"):
                        # Try to find the user by display name or username
                        matched_member = None
                        for member in guild_members:
                            if (member.display_name.lower() == username.lower() or 
                                member.name.lower() == username.lower() or
                                member.global_name and member.global_name.lower() == username.lower()):
                                matched_member = member
                                break
                        
                        if matched_member:
                            scores.append(WordleScore(
                                user=str(matched_member.id),
                                score=score,
                                date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                                is_winner=is_winner
                            ))
                        else:
                            # If we can't resolve the username, store it as-is but mark it
                            scores.append(WordleScore(
                                user=f"unresolved_{username}",
                                score=score,
                                date=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                                is_winner=is_winner
                            ))
    
    return scores if scores else None

def test_parser():
    print("🧪 Testing improved Wordle message parser...")
    print("="*50)
    
    # Create mock guild members
    mock_members = [
        MockMember(id=123456789, name="ethan", display_name="Ethan", global_name="EthanGlobal"),
        MockMember(id=987654321, name="neon", display_name="Neon", global_name="NeonLight"),
        MockMember(id=555666777, name="diego", display_name="diego", global_name="Diego"),
        MockMember(id=111222333, name="bela", display_name="bela"),
        MockMember(id=444555666, name="nico", display_name="NICO"),
    ]
    
    # Test message with mixed mention types
    test_message = """Your group is on a 23 day streak! 🔥 Here are yesterday's results:
👑 3/6: <@123456789> <@987654321>
5/6: @diego @brinka @bela @NICO @lily
6/6: @DiegoK318"""
    
    print("Input message:")
    print(test_message)
    print("\n" + "="*50 + "\n")
    
    scores = parse_wordle_message(test_message, mock_members)
    
    if scores:
        print(f"✅ Successfully parsed {len(scores)} scores:")
        for score in scores:
            user_type = "Discord ID" if score.user.isdigit() else "Unresolved" if score.user.startswith("unresolved_") else "Username"
            winner_text = " (👑 WINNER)" if score.is_winner else ""
            print(f"  - {score.user} ({user_type}): {score.score}/6 on {score.date}{winner_text}")
    else:
        print("❌ Failed to parse message!")
    
    print("\n" + "="*50 + "\n")
    
    # Test another message format
    test_message2 = """Your group is on a 15 day streak! 🔥 Here are yesterday's results:
👑 2/6: <@111222333>
3/6: @ethan @charlie
4/6: @david
6/6: @eve"""
    
    print("Testing another message format...")
    print("Input message:")
    print(test_message2)
    print("\n" + "="*50 + "\n")
    
    scores2 = parse_wordle_message(test_message2, mock_members)
    
    if scores2:
        print(f"✅ Successfully parsed {len(scores2)} scores:")
        for score in scores2:
            user_type = "Discord ID" if score.user.isdigit() else "Unresolved" if score.user.startswith("unresolved_") else "Username"
            winner_text = " (👑 WINNER)" if score.is_winner else ""
            print(f"  - {score.user} ({user_type}): {score.score}/6 on {score.date}{winner_text}")
            
            # Show what the resolved name would be
            if score.user.isdigit():
                for member in mock_members:
                    if str(member.id) == score.user:
                        print(f"    → Resolves to: {member.display_name}")
                        break
    else:
        print("❌ Failed to parse message!")

if __name__ == "__main__":
    test_parser()