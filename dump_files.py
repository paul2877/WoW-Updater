import urllib.request
import json

url = "https://api.curse.tools/v1/cf/mods/256782/files"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    with open("files.json", "w") as f:
        json.dump(data, f, indent=4)
    print("Saved files.json")
