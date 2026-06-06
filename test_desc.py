import urllib.request
import json
from bs4 import BeautifulSoup

url = "https://api.curse.tools/v1/cf/mods/256782/description"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        desc_html = data.get("data", "")
        print("Success! Description HTML length:", len(desc_html))
        print(BeautifulSoup(desc_html, "html.parser").get_text()[:200])
except Exception as e:
    print("Exception:", e)
