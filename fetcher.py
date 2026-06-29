import urllib.request
from urllib.error import HTTPError, URLError 
import json
import re
import os
import random
import time
from datetime import datetime, timezone, timedelta

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")

# Define Philippine Standard Time (UTC+8)
PHT = timezone(timedelta(hours=8))

def get_free_proxies():
    """Fetches a list of free public HTTP proxies to bypass rate limits."""
    try:
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            proxies = response.read().decode('utf-8').strip().split('\n')
            proxies = [p.strip() for p in proxies if p.strip()]
            random.shuffle(proxies) 
            return proxies
    except Exception as e:
        print(f"Warning: Could not fetch proxy list ({e}). Proceeding with direct connection only.")
        return []

def fetch_from_discord(channel_id):
    if not DISCORD_TOKEN:
        print("Skipping Discord Fetch: Hidden vault DISCORD_TOKEN environmental flag missing.")
        return {"error": "CRITICAL: DISCORD_TOKEN environment variable is missing from GitHub Secrets."}
    
    # Increased limit slightly to ensure we catch enough history if posts are months apart
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=10"
    req = urllib.request.Request(url)
    
    req.add_header("Authorization", DISCORD_TOKEN)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
    req.add_header("Accept", "*/*")
    req.add_header("Accept-Language", "en-US,en;q=0.9")
    
    try:
        with urllib.request.urlopen(req) as response:
            messages = json.loads(response.read().decode())
            if not messages:
                return None
            
            extracted_codes = []
            
            for msg in messages:
                message_text = msg.get('content', '')
                for embed in msg.get('embeds', []):
                    if embed.get('title'): message_text += "\n" + str(embed['title'])
                    if embed.get('description'): message_text += "\n" + str(embed['description'])
                    for field in embed.get('fields', []):
                        if field.get('name'): message_text += "\n" + str(field.get('name'))
                        if field.get('value'): message_text += "\n" + str(field.get('value'))
                
                lines = message_text.split("\n")
                
                for raw_line in lines:
                    if not raw_line.strip():
                        continue
                        
                    # 1. Aggressive Cleanup: Strip quotes, markdown, and (edited) tags
                    clean_line = raw_line.replace('"', '').replace("'", "").replace('`', '').replace('*', '')
                    clean_line = re.sub(r'\(edited\).*', '', clean_line).strip()
                    
                    if "expired" in clean_line.lower():
                        continue
                        
                    # 2. Normalize Delimiters: Turn "&" and the word "and" into standard commas
                    clean_line = re.sub(r'(?i)\s+\band\b\s+|\s*&\s*', ',', clean_line)

                    # 3. Prefix Check (Handles: "New Code:", "New Code", "Code:")
                    prefix_match = re.match(r'(?i)^(?:new\s+code[s]?|use\s+code[s]?|enter\s+code[s]?|code[s]?)\s*[:=-]?\s*(.*)', clean_line)
                    if prefix_match:
                        raw_codes_str = prefix_match.group(1)
                        # Split remaining text by comma to catch multiple codes on one line
                        for chunk in raw_codes_str.split(','):
                            candidate = chunk.strip()
                            if len(candidate) > 2 and candidate.lower() not in ["here", "below", "list", "now", "are", "is"]:
                                extracted_codes.append(candidate)
                        continue

                    # 4. Multi-Code Naked Line Check (Handles: "ANGEL, DEMON")
                    if ',' in clean_line:
                        for chunk in clean_line.split(','):
                            candidate = chunk.strip()
                            # Verify it looks like a real code (has numbers or is all caps)
                            if len(candidate) > 3 and (any(char.isdigit() for char in candidate) or candidate.isupper()):
                                extracted_codes.append(candidate)
                        continue

                    # 5. Single Naked Code Check (Handles: "TITAN")
                    match_standalone = re.match(r'^([a-zA-Z0-9_\-]+)$', clean_line)
                    if match_standalone and len(clean_line) > 3:
                        if any(char.isdigit() for char in clean_line) or clean_line.isupper():
                            extracted_codes.append(match_standalone.group(1))
                            continue
                            
            return list(dict.fromkeys(extracted_codes))
            
    except HTTPError as e:
        print(f"HTTP Error processing Discord channel {channel_id}: {e.code}")
        if e.code in [401, 403]:
            return {"error": f"CRITICAL: Discord Token Invalid, Revoked, or Missing Permissions (Error {e.code}). Update GitHub Secrets."}
        return None
    except Exception as e:
        print(f"Extraction error processing Discord channel {channel_id}: {e}")
        return None

def fetch_from_roblox(source_id):
    proxies = get_free_proxies()
    proxy_pool = [None] + proxies[:15] 
    last_error_code = None
    
    for proxy in proxy_pool:
        try:
            if proxy:
                proxy_support = urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
                opener = urllib.request.build_opener(proxy_support)
            else:
                opener = urllib.request.build_opener()

            universe_id = source_id
            try:
                convert_url = f"https://apis.roblox.com/universes/v1/places/{source_id}/universe"
                convert_req = urllib.request.Request(convert_url, headers={"User-Agent": "Mozilla/5.0"})
                with opener.open(convert_req, timeout=5) as response:
                    convert_data = json.loads(response.read().decode("utf-8"))
                    if "universeId" in convert_data:
                        universe_id = convert_data["universeId"]
            except Exception:
                pass 

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
                
        except HTTPError as e:
            last_error_code = e.code
            if proxy is None:
                print(f"  -> Direct connection blocked (Error {e.code}). Engaging Proxy Rotation shield...")
            continue
        except Exception as e:
            continue
            
    print(f"Extraction error processing Roblox ID {source_id}: All proxy attempts exhausted.")
    if last_error_code in [403, 429]:
        return {"error": f"CRITICAL: Roblox API Rate Limit/Block (Error {last_error_code}) across all proxy attempts. Wait 24 hours."}
    return None

def main():
    codes_path = "codes.json"
    notif_path = "notif.json"
    
    if not os.path.exists(codes_path):
        print(f"Error: Target database {codes_path} missing from environment root.")
        return
        
    with open(codes_path, "r", encoding="utf-8") as f:
        database = json.load(f)
        
    if "system_status" in database:
        del database["system_status"]

    if not os.path.exists(notif_path):
        notifs = {"unread_count": 0, "logs": [], "system_state": "Operational"}
    else:
        with open(notif_path, "r", encoding="utf-8") as nf:
            notifs = json.load(nf)

    def add_notification(notif_type, message):
        timestamp = datetime.now(PHT).strftime('%b %d, %I:%M %p PHT')
        notifs["logs"].insert(0, {
            "type": notif_type,
            "message": message,
            "timestamp": timestamp
        })
        notifs["unread_count"] += 1
        if len(notifs["logs"]) > 30:
            notifs["logs"] = notifs["logs"][:30]

    current_time = datetime.now(PHT).isoformat()
    old_system_state = notifs.get("system_state", "Operational")
    run_has_error = False
    latest_error = ""
        
    for game in database.get("games", []):
        source_type = game.get("source_type", "manual")
        source_id = game.get("source_id", "")
        old_codes = set(game.get("codes", []))
        
        if source_type == "discord" and source_id:
            print(f"Querying automated Discord pipeline for: {game['name']}")
            fresh_codes = fetch_from_discord(source_id)
            
            if isinstance(fresh_codes, dict) and "error" in fresh_codes:
                run_has_error = True
                latest_error = fresh_codes["error"]
                print(latest_error)
            elif fresh_codes is not None:
                newly_added = set(fresh_codes) - old_codes
                if newly_added:
                    for code in newly_added:
                        add_notification("info", f"✨ New code found for {game['name']}: {code}")
                
                game["codes"] = fresh_codes
                game["last_updated"] = current_time 
                
            time.sleep(random.uniform(5.0, 15.0))
                
        elif source_type == "roblox" and source_id:
            print(f"Querying automated Roblox description pipeline for: {game['name']}")
            fresh_codes = fetch_from_roblox(source_id)
            
            if isinstance(fresh_codes, dict) and "error" in fresh_codes:
                run_has_error = True
                latest_error = fresh_codes["error"]
                print(latest_error)
            elif fresh_codes is not None:
                newly_added = set(fresh_codes) - old_codes
                if newly_added:
                    for code in newly_added:
                        add_notification("info", f"✨ New code found for {game['name']}: {code}")
                        
                game["codes"] = fresh_codes
                game["last_updated"] = current_time 
                
        else:
            print(f"Preserving explicit static state for manual module: {game['name']}")

    if run_has_error:
        if old_system_state == "Operational":
            add_notification("error", latest_error)
        notifs["system_state"] = "Error"
    else:
        if old_system_state == "Error":
            add_notification("resolved", "✅ SYSTEM RECOVERED: Auto-recovered and fully functional.")
        notifs["system_state"] = "Operational"

    with open(codes_path, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4)
        
    with open(notif_path, "w", encoding="utf-8") as nf:
        json.dump(notifs, nf, indent=4)
        
    print("Database sync workflow terminated successfully.")

if __name__ == "__main__":
    main()
            
