import urllib.request
import json
import re
import os
from datetime import datetime, timezone  # NEW: Added for timestamping

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")

def fetch_from_discord(channel_id):
    if not DISCORD_TOKEN:
        print("Skipping Discord Fetch: Hidden vault DISCORD_TOKEN environmental flag missing.")
        return None
    
    # NEW: Increased limit to 5 to catch multiple codes posted in separate messages!
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=5"
    req = urllib.request.Request(url)
    req.add_header("Authorization", DISCORD_TOKEN)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    
    try:
        with urllib.request.urlopen(req) as response:
            messages = json.loads(response.read().decode())
            if not messages:
                return None
            
            extracted_codes = []
            
            # Loop through all 5 of the most recent messages
            for msg in messages:
                message_text = msg['content']
                lines = message_text.split("\n")
                
                start_parsing = False
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Strip standard markdown (# headers, * bolds, ` codeblocks)
                    clean_line = line.replace('`', '').replace('*', '').replace('#', '').strip()
                    
                    # [Layout 1]: Developer used "Codes:" as a header
                    if "Codes:" in line or clean_line.lower() == "codes":
                        start_parsing = True
                        continue
                    
                    if start_parsing:
                        clean_code = re.sub(r'\(edited\).*', '', clean_line).strip()
                        if clean_code:
                            extracted_codes.append(clean_code)
                    else:
                        # [Layout 2]: "CODE - Reward" format
                        match_layout2 = re.match(r'^([a-zA-Z0-9_\-]+?)\s*[-:]\s+(.*)', clean_line)
                        if match_layout2:
                            extracted_codes.append(match_layout2.group(1))
                            continue
                            
                        # [Layout 3]: Naked Standalone Code (e.g., "5MILVISITS" or "THANKYOU5K")
                        # Rule: Must be a single word (no spaces), > 3 chars, letters/numbers/hyphens only.
                        match_layout3 = re.match(r'^([a-zA-Z0-9_\-]+)$', clean_line)
                        
                        if match_layout3 and len(clean_line) > 3:
                            # Safeguard: To avoid grabbing random chatter like "Enjoy", naked codes
                            # usually contain at least one number OR are typed in ALL CAPS.
                            if any(char.isdigit() for char in clean_line) or clean_line.isupper():
                                extracted_codes.append(match_layout3.group(1))
                            
            # Because we fetched 5 messages, we remove any accidental duplicates before returning
            return list(dict.fromkeys(extracted_codes))
            
    except Exception as e:
        print(f"Extraction error processing Discord channel {channel_id}: {e}")
        return None


def fetch_from_roblox(source_id):
    # Step 1: Automatically try to translate a Place ID into a Universe ID
    universe_id = source_id
    try:
        convert_url = f"https://apis.roblox.com/universes/v1/places/{source_id}/universe"
        convert_req = urllib.request.Request(convert_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(convert_req) as response:
            convert_data = json.loads(response.read().decode("utf-8"))
            if "universeId" in convert_data:
                universe_id = convert_data["universeId"]
    except Exception:
        # If it fails, we assume the user already provided a valid Universe ID
        pass

    # Step 2: Fetch the game description using the correct Universe ID
    url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            for game in data.get("data", []):
                desc = game.get("description", "")
                
                # Look for "Codes:" (case-insensitive) and grab everything after it until a newline
                match = re.search(r'(?i)codes?[\s:]+([^\n]+)', desc)
                if match:
                    raw_line = match.group(1)
                    
                    # Chop off trailing sentences if they didn't use newlines
                    raw_line = re.split(r'[.!|]', raw_line)[0] 
                    
                    # Replace words like "and" or "&" with commas so we can split easily
                    raw_line = re.sub(r'(?i)\band\b|&', ',', raw_line)
                    
                    active_codes = []
                    for chunk in raw_line.split(','):
                        # Extract the exact alphanumeric + hyphen code
                        code_match = re.search(r'([a-zA-Z0-9\-]+)', chunk)
                        if code_match:
                            active_codes.append(code_match.group(1))
                            
                    return active_codes
            return None
    except Exception as e:
        print(f"Extraction error processing Roblox ID {source_id}: {e}")
        return None


def main():
    file_path = "codes.json"
    if not os.path.exists(file_path):
        print("Error: Target database codes.json missing from environment root.")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        database = json.load(f)
        
    # Generate a standard UTC timestamp string for this specific script run
    current_time = datetime.now(timezone.utc).isoformat()
        
    for game in database.get("games", []):
        source_type = game.get("source_type", "manual")
        source_id = game.get("source_id", "")
        
        if source_type == "discord" and source_id:
            print(f"Querying automated Discord pipeline for: {game['name']}")
            fresh_codes = fetch_from_discord(source_id)
            if fresh_codes is not None:
                game["codes"] = fresh_codes
                game["last_updated"] = current_time  # Stamp the check time
                
        elif source_type == "roblox" and source_id:
            print(f"Querying automated Roblox description pipeline for: {game['name']}")
            fresh_codes = fetch_from_roblox(source_id)
            if fresh_codes is not None:
                game["codes"] = fresh_codes
                game["last_updated"] = current_time  # Stamp the check time
                
        else:
            print(f"Preserving explicit static state for manual module: {game['name']}")
            # Notice we do NOT stamp manual games here, because this script didn't check them!

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4)
    print("Database sync workflow terminated successfully.")

if __name__ == "__main__":
    main()
    
