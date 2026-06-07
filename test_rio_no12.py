import json
from downloader import api_request, API_BASE, load_config

config = load_config()
api_key = config.get("api_key")

url = f"{API_BASE}/mods/279257/files?pageSize=200"
data = api_request(url, api_key)
if data and "data" in data:
    for f in data["data"]:
        versions = [g.get('gameVersionName') for g in f.get('sortableGameVersions', [])]
        if not any(v.startswith('12.') for v in versions if v):
            print(f"File: {f['fileName']}")
            print(f"  Versions: {versions}")
            break
