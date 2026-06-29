import urllib.request
import json
import re
import os
import random  # NEW: Added to shuffle proxies
from datetime import datetime, timezone

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")

def get_free_proxies():
    """Fetches a list of free public HTTP proxies to bypass rate limits."""
    try:
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            proxies = response.read().decode('utf-8').strip().split('\n')
            proxies = [p.strip() for p in proxies if p.strip()]
            random.shuffle(proxies) # Shuffle to avoid using the same proxy repeatedly
            return proxies
    except Exception as e:
        print(f"Warning: Could not fetch proxy list ({e}). Proceeding with direct connection only.")
        return []

def fetch_from_discord(channel_id):
    if not DISCORD_TOKEN:
        print("Skipping Discord Fetch: Hidden vault DISCORD_TOKEN environmental flag missing.")
        return None
    
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
            
            for msg in messages:
                # Extract text from standard content AND Discord Embeds
                message_text = msg.get('content', '')
                for embed in msg.get('embeds', []):
                    if embed.get('title'): message_text += "\n" + str(embed['title'])
                    if embed.get('description'): message_text += "\n" + str(embed['description'])
                    for field in embed.get('fields', []):
                        if field.get('name'): message_text += "\n" + str(field.get('name'))
                        if field.get('value'): message_text += "\n" + str(field.get('value'))
                
                lines = message_text.split("\n")
                cleaned_lines = [line.replace('`', '').replace('*', '').replace('#', '').strip() for line in lines]
                cleaned_lines = [line for line in cleaned_lines if line] 
                
                start_parsing = False
                for i, line in enumerate(cleaned_lines):
                    
                    # Global Expiration Filter
                    if "expired" in line.lower():
                        continue
                    if i + 1 < len(cleaned_lines) and "expired" in cleaned_lines[i+1].lower():
                        continue
                    
                    # [Layout 1]: Developer used "Codes:" as a header
                    if "codes:" in line.lower() or line.lower() == "codes":
                        start_parsing = True
                        continue
                    
                    if start_parsing:
                        clean_code = re.sub(r'\(edited\).*', '', line).strip()
                        if clean_code:
                            extracted_codes.append(clean_code)
                    else:
                        # [Layout 4]: Bot Two-Line Format (Code on Line 1, Bullet Reward on Line 2)
                        if i + 1 < len(cleaned_lines) and (cleaned_lines[i+1].startswith('•') or cleaned_lines[i+1].startswith('-')):
                            match_layout4 = re.match(r'^([a-zA-Z0-9_\-]+)$', line)
                            if match_layout4 and len(line) > 3:
                                extracted_codes.append(match_layout4.group(1))
                                continue

                        # [Layout 2]: "CODE - Reward" format
                        match_layout2 = re.match(r'^([a-zA-Z0-9_\-]+?)\s*[-:]\s+(.*)', line)
                        if match_layout2:
                            extracted_codes.append(match_layout2.group(1))
                            continue
                            
                        # [Layout 3]: Naked Standalone Code
                        match_layout3 = re.match(r'^([a-zA-Z0-9_\-]+)$', line)
                        if match_layout3 and len(line) > 3:
                            if any(char.isdigit() for char in line) or line.isupper():
                                extracted_codes.append(match_layout3.group(1))
                            
            return list(dict.fromkeys(extracted_codes))
            
    except Exception as e:
        print(f"Extraction error processing Discord channel {channel_id}: {e}")
        return None


def fetch_from_roblox(source_id):
    proxies = get_free_proxies()
    # Try a Direct Connection first (None), then fall back to top 15 proxies
    proxy_pool = [None] + proxies[:15] 
    
    for proxy in proxy_pool:
        try:
            # Build custom opener for this specific iteration
            if proxy:
                proxy_support = urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
                opener = urllib.request.build_opener(proxy_support)
            else:
                opener = urllib.request.build_opener()

            # Step 1: Automatically try to translate a Place ID into a Universe ID
            universe_id = source_id
            try:
                convert_url = f"https://apis.roblox.com/universes/v1/places/{source_id}/universe"
                convert_req = urllib.request.Request(convert_url, headers={"User-Agent": "Mozilla/5.0"})
                with opener.open(convert_req, timeout=5) as response:
                    convert_data = json.loads(response.read().decode("utf-8"))
                    if "universeId" in convert_data:
                        universe_id = convert_data["universeId"]
            except Exception:
                pass # Usually implies it's already a Universe ID, continue

            # Step 2: Fetch the game description using the correct Universe ID
            url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            
            with opener.open(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                for game in data.get("data", []):
                    desc = game.get("description", "")
                    
                    match = re.search(r'(?i)codes?[\s:]+([^\n]+)', desc)
                    if match:
                        raw_line = match.group(1)
                        raw_line = re.split(r'[.!|]', raw_line)[0] 
                        raw_line = re.sub(r'(?i)\band\b|&', ',', raw_line)
                        
                        active_codes = []
                        for chunk in raw_line.split(','):
                            code_match = re.search(r'([a-zA-Z0-9\-]+)', chunk)
                            if code_match:
                                active_codes.append(code_match.group(1))
                                
                        return active_codes
                return None
                
        except Exception as e:
            # If the direct connection fails, trigger the proxy loop
            if proxy is None:
                print(f"  -> Direct connection blocked/failed. Engaging Proxy Rotation shield...")
            # Silently continue to try the next proxy in the pool
            continue
            
    print(f"Extraction error processing Roblox ID {source_id}: All proxy attempts exhausted.")
    return None


def main():
    file_path = "codes.json"
    if not os.path.exists(file_path):
        print("Error: Target database codes.json missing from environment root.")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        database = json.load(f)
        
    current_time = datetime.now(timezone.utc).isoformat()
        
    for game in database.get("games", []):
        source_type = game.get("source_type", "manual")
        source_id = game.get("source_id", "")
        
        if source_type == "discord" and source_id:
            print(f"Querying automated Discord pipeline for: {game['name']}")
            fresh_codes = fetch_from_discord(source_id)
            if fresh_codes is not None:
                game["codes"] = fresh_codes
                game["last_updated"] = current_time 
                
        elif source_type == "roblox" and source_id:
            print(f"Querying automated Roblox description pipeline for: {game['name']}")
            fresh_codes = fetch_from_roblox(source_id)
            if fresh_codes is not None:
                game["codes"] = fresh_codes
                game["last_updated"] = current_time 
                
        else:
            print(f"Preserving explicit static state for manual module: {game['name']}")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4)
    print("Database sync workflow terminated successfully.")

if __name__ == "__main__":
    main()
                                 
