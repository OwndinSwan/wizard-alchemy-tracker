import urllib.request
import json
import re

# Add your games here: "UniverseID": "Display Name"
TARGET_GAMES = {
    "10006104044": "Wizard Alchemy",
    "4746011041": "Untitled Boxing Game" # Example ID
}

# Combine all IDs to make a single, fast API request
universe_ids = ",".join(TARGET_GAMES.keys())
api_url = f"https://games.roblox.com/v1/games?universeIds={universe_ids}"

try:
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    data = json.loads(response.read())
    
    # New JSON structure to hold multiple games
    final_output = {
        "status": "success",
        "games": []
    }
    
    # Loop through every game returned by Roblox
    for game in data.get('data', []):
        uid = str(game['id'])
        name = TARGET_GAMES.get(uid, game.get('name', 'Unknown'))
        desc = game.get('description', '')
        
        # Search the description for codes
        match = re.search(r'codes?[\s:]+([A-Z0-9,\s]+)', desc, re.IGNORECASE)
        
        active_codes = []
        if match:
            # Clean up the text and split into a list
            raw_codes = match.group(1).replace('and', '').replace(' ', '')
            active_codes = [code for code in raw_codes.split(',') if code]
            
        # Add the results to our master list
        final_output["games"].append({
            "name": name,
            "codes": active_codes
        })
        
    # Save the combined data
    with open('codes.json', 'w') as f:
        json.dump(final_output, f, indent=4)
        
except Exception as e:
    print(f"Error: {e}")
