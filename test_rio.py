import json
from downloader import api_request, API_BASE, load_config

config = load_config()
api_key = config.get("api_key")

url = f"{API_BASE}/mods/279257/files?pageSize=5"
data = api_request(url, api_key)
if data and "data" in data:
    for f in data["data"]:
        print(f"File: {f['fileName']}")
        for gv in f.get('sortableGameVersions', []):
            print(f"  - {gv.get('gameVersionName')} (Type: {gv.get('gameVersionTypeId')})")
