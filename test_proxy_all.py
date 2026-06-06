import urllib.request
import json

base = "https://api.curse.tools/v1/cf"
addon_id = 256782

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode())
    except Exception as e:
        return str(e)

print("Mod Info:", "data" in fetch(f"{base}/mods/{addon_id}"))
files = fetch(f"{base}/mods/{addon_id}/files")
print("Files:", "data" in files)
file_id = files["data"][0]["id"]
print("Download URL:", fetch(f"{base}/mods/{addon_id}/files/{file_id}/download-url"))
