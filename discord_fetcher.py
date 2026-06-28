import urllib.request
import json
import re
import os

# ==========================================
# CONFIGURATION (Use GitHub Secrets or fill in)
# ==========================================
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_ALT_ACCOUNT_TOKEN")
CHANNEL_ID = "1479652832155275307"  # Replace with the actual channel ID
# ==========================================

def fetch_discord_codes():
    url = f"https://discord.com/api/v9/channels/{CHANNEL_ID}/messages?limit=1"
    req = urllib.request.Request(url)
    
    # Passing a user token requires the raw token string in the Authorization header
    req.add_header("Authorization", DISCORD_TOKEN)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    try:
        with urllib.request.urlopen(req) as response:
            messages = json.loads(response.read().decode())
            if not messages:
                print("No messages found.")
                return
            
            # Grab the latest message body
            message_text = messages[0]['content']
            print("Raw Message Received:\n", message_text)
            
            # Parse the text block based on the layout in 1000040938.jpg
            lines = message_text.split("\n")
            extracted_codes = []
            
            start_parsing = False
            for line in lines:
                line = line.strip()
                if "Codes:" in line:
                    start_parsing = True
                    continue
                
                if start_parsing and line:
                    # Strip out any lingering edits or annotations like '(edited)'
                    clean_code = re.sub(r'\(edited\).*', '', line).replace('`', '').strip()
                    if clean_code:
                        extracted_codes.append(clean_code)
            
            print("Extracted Codes:", extracted_codes)
            update_local_json(extracted_codes)

    except Exception as e:
        print(f"Failed to fetch from Discord: {e}")

def update_local_json(new_codes):
    file_path = "codes.json"
    
    # Standard structure expected by your index.html
    data = {
        "status": "success",
        "games": [
            {
                "name": "Wizard Alchemy",
                "codes": new_codes
            }
        ]
    }
    
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
    print("codes.json updated successfully locally.")

if __name__ == "__main__":
    fetch_discord_codes()
