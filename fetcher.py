import urllib.request
import json
import re
import os

# Wizard Alchemy's Universe ID 
universe_id = "10006104044" 
api_url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"

try:
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    data = json.loads(response.read())
    
    description = data['data'][0]['description']
    
    # Extract codes from the description using regex
    match = re.search(r'codes?[\s:]+([A-Z0-9,\s]+)', description, re.IGNORECASE)
    
    if match:
        raw_codes = match.group(1).replace('and', '').replace(' ', '')
        active_codes = [code for code in raw_codes.split(',') if code] 
        
        output = {
            "game": "Wizard Alchemy",
            "codes": active_codes,
            "status": "success"
        }
        
        with open('codes.json', 'w') as f:
            json.dump(output, f, indent=4)
            
except Exception as e:
    print(f"Error: {e}")
  
