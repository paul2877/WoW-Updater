import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import json
import urllib.parse

def test_selenium():
    options = uc.ChromeOptions()
    options.headless = True # Try headless first
    # driver = uc.Chrome(options=options) # undetected_chromedriver doesn't always support headless well for CF
    
    # We will run non-headless but minimal window
    print("Starting Chrome...")
    driver = uc.Chrome(headless=False)
    
    query = "hero"
    url = f"https://www.curseforge.com/api/v1/mods/search?gameId=1&classId=6&searchFilter={query}&sortField=2&pageSize=50"
    print(f"Navigating to {url}")
    
    driver.get(url)
    
    # Wait for Cloudflare to pass
    print("Waiting 8 seconds for Cloudflare...")
    time.sleep(8)
    
    try:
        # If it's a JSON response, Chrome wraps it in a <pre> tag
        element = driver.find_element(By.TAG_NAME, "pre")
        text = element.text
        data = json.loads(text)
        print("Success! Items found:", len(data.get("data", [])))
        if data.get("data"):
            print("First item:", data["data"][0]["name"])
    except Exception as e:
        print("Failed to get JSON:", e)
        print("Page Title:", driver.title)
    finally:
        driver.quit()

if __name__ == "__main__":
    test_selenium()
