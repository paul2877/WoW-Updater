import json
from downloader import api_request, API_BASE, load_config

config = load_config()
api_key = config.get("api_key")

url = f"{API_BASE}/mods/279257/files?pageSize=200"
data = api_request(url, api_key)
if data and "data" in data:
    print(f"Items returned: {len(data['data'])}")
    if data['data']:
        print(f"Oldest file in this batch: {data['data'][-1]['fileName']}")
