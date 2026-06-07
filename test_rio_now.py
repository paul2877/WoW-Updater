import json
from downloader import get_addon_files, load_config

config = load_config()
api_key = config.get("api_key")
target_version = config.get("game_version") # 11.1.5
target_type_id = 517

files = get_addon_files(279257, api_key)
if files:
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

    if best_file:
        print(f"Target: {target_version}")
        print(f"Selected: {best_file['fileName']}")
        print(f"Versions: {[gv.get('gameVersionName') for gv in best_file.get('sortableGameVersions', [])]}")
    else:
        print("No best file selected.")
