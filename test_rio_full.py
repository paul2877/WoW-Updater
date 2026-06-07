import json
from downloader import api_request, API_BASE, load_config

config = load_config()
api_key = config.get("api_key")

url = f"{API_BASE}/mods/279257/files?pageSize=200"
data = api_request(url, api_key)
if data and "data" in data:
    found_11 = False
    for f in data["data"]:
        for gv in f.get('sortableGameVersions', []):
            if gv.get('gameVersionName', '').startswith('11.'):
                print(f"Found 11.x file: {f['fileName']}")
                found_11 = True
                break
        if found_11:
            break
    if not found_11:
        print("NO 11.x FILES FOUND IN TOP 200!")
