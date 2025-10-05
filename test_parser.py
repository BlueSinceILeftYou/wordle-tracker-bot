#!/usr/bin/env python3
"""Test script for the Wordle message parser"""

import re
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class WordleScore:
    user: str
    score: int
    date: str
    is_winner: bool = False

def parse_wordle_message(message_content: str):
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

def test_parser():
    print("Starting test...")
    
    # Test message from your example
    test_message = """Your group is on a 20 day streak! 🔥 Here are yesterday's results:
👑 3/6: @bela
4/6: @diego @lily
5/6: @JoshK318 @NICO"""
    
    print("Testing message parser...")
    print("Input message:")
    print(test_message)
    print("\n" + "="*50 + "\n")
    
    try:
        scores = parse_wordle_message(test_message)
        
        if scores:
            print(f"Successfully parsed {len(scores)} scores:")
            for score in scores:
                winner_text = " (WINNER)" if score.is_winner else ""
                print(f"- {score.user}: {score.score}/6 on {score.date}{winner_text}")
        else:
            print("Failed to parse message!")
    except Exception as e:
        print(f"Error parsing message: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*50 + "\n")
    
    # Test another variation
    test_message2 = """Your group is on a 15 day streak! 🔥 Here are yesterday's results:
👑 2/6: @alice
3/6: @bob @charlie
4/6: @david
6/6: @eve"""
    
    print("Testing another message format...")
    print("Input message:")
    print(test_message2)
    print("\n" + "="*50 + "\n")
    
    try:
        scores2 = parse_wordle_message(test_message2)
        
        if scores2:
            print(f"Successfully parsed {len(scores2)} scores:")
            for score in scores2:
                winner_text = " (WINNER)" if score.is_winner else ""
                print(f"- {score.user}: {score.score}/6 on {score.date}{winner_text}")
        else:
            print("Failed to parse message!")
    except Exception as e:
        print(f"Error parsing message: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Script started")
    test_parser()
    print("Script completed")