import urllib.request
import json

url = "https://api.curse.tools/v1/cf/mods/256782/files"

req = urllib.request.Request(url, headers={
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Success! Files found:", len(data.get("data", [])))
        if data.get("data"):
            print("First file versions:")
            for gv in data["data"][0].get("gameVersions", []):
                print("-", gv)
except Exception as e:
    print("Exception:", e)
    if hasattr(e, 'read'):
        print("Body:", e.read().decode())
