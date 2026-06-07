import os
import json
from downloader import get_latest_file, load_config

config = load_config()
api_key = config.get("api_key")

def dummy_log(msg):
    print(msg)

best = get_latest_file(279257, api_key, "11.1.7", log_callback=dummy_log)
if best:
    print(f"Selected: {best['fileName']}")
    print(f"Versions: {[gv.get('gameVersionName') for gv in best.get('sortableGameVersions', []) if gv.get('gameVersionName')]}")
