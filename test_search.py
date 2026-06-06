import urllib.request
import json

url = "https://www.curseforge.com/api/v1/mods/search?gameId=1&classId=6&searchFilter=hero&sortField=2&pageSize=50"
req = urllib.request.Request(url, headers={
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Success! Items:", len(data.get("data", [])))
except Exception as e:
    print("Exception:", e)
    if hasattr(e, 'read'):
        print("Body:", e.read().decode())
