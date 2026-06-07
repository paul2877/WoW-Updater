import json
from downloader import api_request, API_BASE, load_config

config = load_config()
api_key = config.get("api_key")

url = f"{API_BASE}/mods/search?gameId=1&slug=weakauras-2&pageSize=1"
data = api_request(url, api_key)
if data and "data" in data and len(data["data"]) > 0:
    mod = data["data"][0]
    print(f"ID: {mod['id']} | Name: {mod['name']}")
    url2 = f"{API_BASE}/mods/{mod['id']}/files?pageSize=10"
    data2 = api_request(url2, api_key)
    if data2 and "data" in data2:
        for f in data2["data"]:
            print(f"  File: {f['fileName']} | Versions: {f.get('gameVersions')}")
