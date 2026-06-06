import urllib.request
import json

url = "https://api.curse.tools/v1/cf/mods/256782"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Success:", data["data"]["name"])
except Exception as e:
    print("Exception:", e)
