import urllib.request
import json

url = "https://addons.wago.io/api/search?q=dbm"
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
})
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Success! Items found:", len(data))
        if data:
            print("First item:", data[0].get("name"))
except Exception as e:
    print("Exception:", e)
    if hasattr(e, 'read'):
        print("Body:", e.read().decode())
