import re
from datetime import datetime, timedelta

# Simple test function
def test_parsing():
    test_message = """Your group is on a 20 day streak! 🔥 Here are yesterday's results:
👑 3/6: @bela
4/6: @diego @lily
5/6: @JoshK318 @NICO"""
    
    print("Testing regex patterns...")
    
    # Check streak pattern
    streak_pattern = r"Your group is on a (\d+) day streak!"
    streak_match = re.search(streak_pattern, test_message)
    print(f"Streak match: {streak_match.group(1) if streak_match else 'None'}")
    
    # Check score patterns
    score_pattern = r"(👑\s*)?(\d+)/6:\s*(.+)"
    lines = test_message.split('\n')
    
    for i, line in enumerate(lines):
        match = re.search(score_pattern, line)
        if match:
            print(f"Line {i}: {line}")
            print(f"  Crown: {match.group(1) is not None}")
            print(f"  Score: {match.group(2)}")
            print(f"  Users text: {match.group(3)}")
            
            # Extract usernames
            users = re.findall(r'@(\w+)', match.group(3))
            print(f"  Users: {users}")
            print()

if __name__ == "__main__":
    test_parsing()