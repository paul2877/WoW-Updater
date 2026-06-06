import urllib.request
import json

url = "https://api.curse.tools/v1/cf/mods/search?gameId=1&classId=6&searchFilter=hero&sortField=2&pageSize=50"
req = urllib.request.Request(url, headers={
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Success! Items found:", len(data.get("data", [])))
        if data.get("data"):
            print("First item:", data["data"][0]["name"])
except Exception as e:
    print("Exception:", e)
    if hasattr(e, 'read'):
        print("Body:", e.read().decode())
