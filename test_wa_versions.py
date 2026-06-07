import json
from downloader import api_request, API_BASE, load_config

config = load_config()
api_key = config.get("api_key")

url = f"{API_BASE}/mods/68001/files?pageSize=50"
data = api_request(url, api_key)
versions_found = set()
if data and "data" in data:
    for f in data["data"]:
        for gv in f.get('sortableGameVersions', []):
            versions_found.add(gv.get('gameVersionName'))

print("Available WA Game Versions:")
print(sorted(list(versions_found)))
