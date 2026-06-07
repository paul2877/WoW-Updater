import urllib.request
import urllib.error
import json
import os

token = os.getenv("GITHUB_TOKEN", "YOUR_TOKEN_HERE")
repo = "paul2877/WoW-Updater"
file_path = r"dist\WoW Updater V9.exe"

# 1. Create Release
release_data = {
    "tag_name": "v1.3",
    "name": "WoW Updater v1.3",
    "body": "Исправлена критическая проблема с установкой Retail-версий аддонов (например, WeakAuras), когда программа ошибочно качала Classic-версию.\n\nСкачайте `WoW Updater V9.exe` ниже, чтобы начать пользоваться!",
    "draft": False,
    "prerelease": False
}

req = urllib.request.Request(
    f"https://api.github.com/repos/{repo}/releases",
    data=json.dumps(release_data).encode("utf-8"),
    headers={
        "Authorization": f"token {token}",
        "Content-Type": "application/json",
        "User-Agent": "WoWUpdater"
    }
)

try:
    with urllib.request.urlopen(req) as response:
        release_info = json.loads(response.read().decode())
        upload_url = release_info["upload_url"].split("{")[0]
        print("Release created! ID:", release_info["id"])
except urllib.error.HTTPError as e:
    if e.code == 422: # Already exists, we can fetch it
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/releases/tags/v1.0",
            headers={"Authorization": f"token {token}", "User-Agent": "WoWUpdater"}
        )
        with urllib.request.urlopen(req) as response:
            release_info = json.loads(response.read().decode())
            upload_url = release_info["upload_url"].split("{")[0]
            print("Found existing release! ID:", release_info["id"])
    else:
        print("Error creating release:", e.read().decode())
        exit(1)

# 2. Upload Asset
print("Uploading asset...")
with open(file_path, "rb") as f:
    file_data = f.read()

upload_req = urllib.request.Request(
    f"{upload_url}?name=WoW_Updater_V9.exe",
    data=file_data,
    headers={
        "Authorization": f"token {token}",
        "Content-Type": "application/octet-stream",
        "User-Agent": "WoWUpdater"
    }
)

try:
    with urllib.request.urlopen(upload_req) as response:
        print("Asset uploaded successfully!")
except urllib.error.HTTPError as e:
    print("Error uploading asset:", e.read().decode())
