import urllib.request
from urllib.error import HTTPError, URLError # NEW: Imported to catch exact network errors
import json
import re
import os
import random
import time
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
            random.shuffle(proxies) 
            return proxies
    except Exception as e:
        print(f"Warning: Could not fetch proxy list ({e}). Proceeding with direct connection only.")
        return []

def fetch_from_discord(channel_id):
    if not DISCORD_TOKEN:
        print("Skipping Discord Fetch: Hidden vault DISCORD_TOKEN environmental flag missing.")
        return {"error": "CRITICAL: DISCORD_TOKEN environment variable is missing from GitHub Secrets."}
    
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=5"
    req = urllib.request.Request(url)
    
    # Anti-Monitoring Measure: Perfect Chrome Browser Fingerprinting
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
                cleaned_lines = [line.replace('`', '').replace('*', '').replace('#', '').strip() for line in lines]
                cleaned_lines = [line for line in cleaned_lines if line] 
                
                start_parsing = False
                for i, line in enumerate(cleaned_lines):
                    
                    if "expired" in line.lower():
                        continue
                    if i + 1 < len(cleaned_lines) and "expired" in cleaned_lines[i+1].lower():
                        continue
                    
                    if "codes:" in line.lower() or line.lower() == "codes":
                        start_parsing = True
                        continue
                    
                    if start_parsing:
                        clean_code = re.sub(r'\(edited\).*', '', line).strip()
                        if clean_code:
                            extracted_codes.append(clean_code)
                    else:
                        # Layout 6: Emoji/Symbol List
                        match_layout6 = re.match(r'^[^a-zA-Z0-9]+\s*([A-Z0-9_\-]+)$', line)
                        if match_layout6 and len(line) > 3:
                            candidate = match_layout6.group(1)
                            if any(char.isdigit() for char in candidate) or candidate.isupper():
                                extracted_codes.append(candidate)
                                continue

                        # Layout 5: Inline Keyword
                        match_layout5 = re.search(r'(?i)(?:(?:use|new|enter)\s+code[s]?\s*[:=]?|code[s]?\s*[:=])\s*["\']?([a-zA-Z0-9_\-]+)["\']?', line)
                        if match_layout5:
                            candidate = match_layout5.group(1)
                            if len(candidate) > 2 and candidate.lower() not in ["here", "below", "list", "now", "are", "is"]:
                                extracted_codes.append(candidate)
                                continue

                        # Layout 4: Bot Two-Line Format
                        if i + 1 < len(cleaned_lines) and (cleaned_lines[i+1].startswith('•') or cleaned_lines[i+1].startswith('-')):
                            match_layout4 = re.match(r'^([a-zA-Z0-9_\-]+)$', line)
                            if match_layout4 and len(line) > 3:
                                extracted_codes.append(match_layout4.group(1))
                                continue

                        # Layout 2: "CODE - Reward" format
                        match_layout2 = re.match(r'^([a-zA-Z0-9_\-]+?)\s*[-:]\s+(.*)', line)
                        if match_layout2:
                            extracted_codes.append(match_layout2.group(1))
                            continue
                            
                        # Layout 3: Naked Standalone Code
                        match_layout3 = re.match(r'^([a-zA-Z0-9_\-]+)$', line)
                        if match_layout3 and len(line) > 3:
                            if any(char.isdigit() for char in line) or line.isupper():
                                extracted_codes.append(match_layout3.group(1))
                            
            return list(dict.fromkeys(extracted_codes))
            
    except HTTPError as e:
        # Sentinel catches Discord specific bans/token revocations
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
    
    # Sentinel catches Roblox IP bans if ALL proxies fail
    if last_error_code in [403, 429]:
        return {"error": f"CRITICAL: Roblox API Rate Limit/Block (Error {last_error_code}) across all proxy attempts. Wait 24 hours."}
    return None


def main():
    file_path = "codes.json"
    if not os.path.exists(file_path):
        print("Error: Target database codes.json missing from environment root.")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        database = json.load(f)
        
    current_time = datetime.now(timezone.utc).isoformat()
    
    # Ensure system_status exists, default to Operational if this is a fresh run without errors
    if "system_status" not in database:
        database["system_status"] = "Operational"
        
    for game in database.get("games", []):
        source_type = game.get("source_type", "manual")
        source_id = game.get("source_id", "")
        
        if source_type == "discord" and source_id:
            print(f"Querying automated Discord pipeline for: {game['name']}")
            fresh_codes = fetch_from_discord(source_id)
            
            # Catch Sentinel Dict response
            if isinstance(fresh_codes, dict) and "error" in fresh_codes:
                database["system_status"] = fresh_codes["error"]
                print(fresh_codes["error"])
            elif fresh_codes is not None:
                game["codes"] = fresh_codes
                game["last_updated"] = current_time 
                
            # Anti-Monitoring Measure: Randomized network jitter between 5 and 15 seconds
            time.sleep(random.uniform(5.0, 15.0))
                
        elif source_type == "roblox" and source_id:
            print(f"Querying automated Roblox description pipeline for: {game['name']}")
            fresh_codes = fetch_from_roblox(source_id)
            
            # Catch Sentinel Dict response
            if isinstance(fresh_codes, dict) and "error" in fresh_codes:
                database["system_status"] = fresh_codes["error"]
                print(fresh_codes["error"])
            elif fresh_codes is not None:
                game["codes"] = fresh_codes
                game["last_updated"] = current_time 
                
        else:
            print(f"Preserving explicit static state for manual module: {game['name']}")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4)
    print("Database sync workflow terminated successfully.")

if __name__ == "__main__":
    main()
        
