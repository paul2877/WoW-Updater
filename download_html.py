import urllib.request

url = "https://www.curseforge.com/wow/addons/search?search=hero"
req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml"
})
try:
    with urllib.request.urlopen(req) as response:
        with open("search.html", "w", encoding="utf-8") as f:
            f.write(response.read().decode())
        print("Saved to search.html")
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        with open("search.html", "w", encoding="utf-8") as f:
            f.write(e.read().decode())
        print("Saved error body to search.html")
