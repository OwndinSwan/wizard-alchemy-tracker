import urllib.request
import json
import re
import os

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")

def fetch_from_discord(channel_id):
    if not DISCORD_TOKEN:
        print("Skipping Discord Fetch: Hidden vault DISCORD_TOKEN environmental flag missing.")
        return None
    
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=1"
    req = urllib.request.Request(url)
    req.add_header("Authorization", DISCORD_TOKEN)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    
    try:
        with urllib.request.urlopen(req) as response:
            messages = json.loads(response.read().decode())
            if not messages:
                return None
            
            message_text = messages[0]['content']
            lines = message_text.split("\n")
            extracted_codes = []
            
            start_parsing = False
            for line in lines:
                line = line.strip()
                if "Codes:" in line:
                    start_parsing = True
                    continue
                
                if start_parsing and line:
                    # Clean up trailing notes and strip backtick formatting
                    clean_code = re.sub(r'\(edited\).*', '', line).replace('`', '').strip()
                    if clean_code:
                        extracted_codes.append(clean_code)
            return extracted_codes
    except Exception as e:
        print(f"Extraction error processing Discord channel {channel_id}: {e}")
        return None

def fetch_from_roblox(universe_id):
    url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            for game in data.get("data", []):
                desc = game.get("description", "")
                match = re.search(r'codes?[\s:]+([A-Z0-9,\s]+?)(?:\s+[a-z]|\!|\.|$)', desc)
                if match:
                    raw_codes = match.group(1).replace("and", "").replace(" ", "")
                    return [c for c in raw_codes.split(",") if c]
            return None
    except Exception as e:
        print(f"Extraction error processing Roblox Universe {universe_id}: {e}")
        return None

def main():
    file_path = "codes.json"
    if not os.path.exists(file_path):
        print("Error: Target database codes.json missing from environment root.")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        database = json.load(f)
        
    for game in database.get("games", []):
        source_type = game.get("source_type", "manual")
        source_id = game.get("source_id", "")
        
        if source_type == "discord" and source_id:
            print(f"Querying automated Discord pipeline for: {game['name']}")
            fresh_codes = fetch_from_discord(source_id)
            if fresh_codes is not None:
                game["codes"] = fresh_codes
                
        elif source_type == "roblox" and source_id:
            print(f"Querying automated Roblox description pipeline for: {game['name']}")
            fresh_codes = fetch_from_roblox(source_id)
            if fresh_codes is not None:
                game["codes"] = fresh_codes
                
        else:
            print(f"Preserving explicit static state for manual module: {game['name']}")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4)
    print("Database sync workflow terminated successfully.")

if __name__ == "__main__":
    main()
    
