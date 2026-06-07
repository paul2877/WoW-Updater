import json
from downloader import api_request, API_BASE, load_config

config = load_config()
api_key = config.get("api_key")
target_version = config.get("target_version")
target_type_id = 517

# WA id is 68001
url = f"{API_BASE}/mods/68001/files?pageSize=50"
data = api_request(url, api_key)
if data and "data" in data:
    files = data["data"]
    
    exact_matches = []
    if target_version:
        for f in files:
            for gv in f.get('sortableGameVersions', []):
                if target_version in gv.get('gameVersionName', ''):
                    exact_matches.append(f)
                    break
                    
    matching_files = exact_matches
    if not matching_files:
        matching_files = [f for f in files if any(gv.get('gameVersionTypeId') == target_type_id for gv in f.get('sortableGameVersions', []))]
        
        if not matching_files:
            for f in files:
                for gv in f.get('sortableGameVersions', []):
                    name = gv.get('gameVersionName', '')
                    if target_type_id == 517 and ('11.' in name or '12.' in name):
                        matching_files.append(f)
                        break

    if not matching_files:
        matching_files = files

    best_file = None
    for release_type in [1, 2, 3]:
        for f in matching_files:
            if f.get('releaseType') == release_type:
                best_file = f
                break
        if best_file:
            break

    if not best_file and matching_files:
        best_file = matching_files[0]

    print(f"Target version: {target_version}")
    if best_file:
        print(f"Best file selected: {best_file['fileName']}")
        versions = [gv.get("gameVersionName") for gv in best_file.get("sortableGameVersions", [])]
        print(f"File versions: {versions[:5]}...")
        print(f"Release Type: {best_file.get('releaseType')}")
    else:
        print("No best file found.")
