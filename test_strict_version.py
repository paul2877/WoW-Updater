import json
from downloader import api_request, API_BASE, load_config

config = load_config()
api_key = config.get("api_key")

url = f"{API_BASE}/mods/279257/files?pageSize=200"
data = api_request(url, api_key)

def is_newer(v1, v2):
    # returns True if v1 > v2
    def parse(v):
        try:
            return [int(x) for x in v.split('.')]
        except:
            return [0,0,0]
    return parse(v1) > parse(v2)

if data and "data" in data:
    for f in data["data"]:
        versions = [g.get('gameVersionName') for g in f.get('sortableGameVersions', []) if g.get('gameVersionName')]
        
        # Check if any version is newer than 11.1.7
        has_newer = any(is_newer(v, '11.1.7') for v in versions)
        has_exact = any('11.1.7' in v for v in versions)
        
        if has_exact and not has_newer:
            print(f"FOUND STRICT 11.1.7: {f['fileName']}")
            print(f"  Versions: {versions}")
            break
    else:
        print("NO STRICT 11.1.7 FOUND (all 11.1.7 files also contain newer tags like 11.2.x)")
