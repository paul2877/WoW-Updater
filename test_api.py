import requests
import json

with open("config.json", "r") as f:
    config = json.load(f)

key = config["api_key"]

url = "https://api.curseforge.com/v1/mods/3358"
headers = {
    "Accept": "application/json",
    "x-api-key": key,
    "User-Agent": "Mozilla/5.0"
}

try:
    res = requests.get(url, headers=headers)
    print("Status:", res.status_code)
    print("Headers:", res.headers)
    print("Body:", res.text)
except Exception as e:
    print("Exception:", e)
