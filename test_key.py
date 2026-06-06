import urllib.request
import json

url = "https://api.curseforge.com/v1/mods/256782"
api_key = "$2a$10$vodiB/o3RcTLvPt4dG21l.IJelxaY33WJlk922TlBYW2OahYNfvhC"

req = urllib.request.Request(url, headers={
    "Accept": "application/json",
    "x-api-key": api_key,
    "User-Agent": "Mozilla/5.0"
})
try:
    with urllib.request.urlopen(req) as response:
        print("Success:", json.loads(response.read().decode())["data"]["name"])
except Exception as e:
    print("Exception:", e)
    if hasattr(e, 'read'):
        print("Body:", e.read().decode())
