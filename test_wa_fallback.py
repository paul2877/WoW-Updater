import json
from downloader import api_request, API_BASE, load_config

config = load_config()
api_key = config.get("api_key")
target_version = config.get("game_version") # e.g. "11.1.5"
target_type_id = 517

url = f"{API_BASE}/mods/65387/files?pageSize=10"
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
        
        # New fallback filter
        if target_version and target_type_id == 517:
            if "War Within" in target_version:
                major_version = "11."
            else:
                major_version = target_version.split('.')[0] + '.'
            
            filtered = []
            for f in matching_files:
                for gv in f.get('sortableGameVersions', []):
                    name = gv.get('gameVersionName', '')
                    if name.startswith(major_version):
                        filtered.append(f)
                        break
            if filtered:
                matching_files = filtered
            else:
                # Still no match? Filter out 12.x if we are aiming for 11.x
                if major_version == "11.":
                    matching_files = [f for f in matching_files if not any(gv.get('gameVersionName', '').startswith('12.') for gv in f.get('sortableGameVersions', []))]

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

    if best_file:
        print(f"Target version: {target_version}")
        print(f"Best file selected: {best_file['fileName']}")
        versions = [gv.get("gameVersionName") for gv in best_file.get("sortableGameVersions", [])]
        print(f"File versions: {versions[:5]}")
