import urllib.request
import json
import re

TARGET_GAMES = {
    "10006104044": "Wizard Alchemy"
}

universe_ids = ",".join(TARGET_GAMES.keys())
api_url = f"https://games.roblox.com/v1/games?universeIds={universe_ids}"

try:
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))
    
    final_output = {
        "status": "success",
        "games": []
    }
    
    for game in data.get("data", []):
        uid = str(game.get("id", ""))
        name = TARGET_GAMES.get(uid, game.get("name", "Unknown"))
        desc = game.get("description", "")
        
        # Tightened Regex to stop catching trailing words
        match = re.search(r'codes?[\s:]+([A-Z0-9,\s]+?)(?:\s+[a-z]|\!|\.|$)', desc)
        
        active_codes = []
        if match:
            raw_codes = match.group(1).replace("and", "").replace(" ", "")
            active_codes = [c for c in raw_codes.split(",") if c]
            
        final_output["games"].append({
            "name": name,
            "codes": active_codes
        })
        
    with open("codes.json", "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4)
        print("Successfully generated codes.json")
        
except Exception as e:
    print(f"Execution failed: {e}")
    raise e
    
