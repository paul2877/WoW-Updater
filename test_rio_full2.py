import json
from downloader import api_request, API_BASE, load_config

config = load_config()
api_key = config.get("api_key")

url = f"{API_BASE}/mods/279257/files?pageSize=100"
data = api_request(url, api_key)
if data and "data" in data:
    count = 0
    for f in data["data"]:
        for gv in f.get('sortableGameVersions', []):
            if gv.get('gameVersionName', '').startswith('11.'):
                print(f"File: {f['fileName']}")
                print("  Versions:", [g.get('gameVersionName') for g in f.get('sortableGameVersions', [])])
                count += 1
                break
        if count >= 3:
            break
