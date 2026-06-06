import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time

def test():
    options = uc.ChromeOptions()
    options.headless = True
    driver = uc.Chrome(options=options)
    
    url = "https://www.curseforge.com/wow/search?class=addons&search=hero"
    print("Navigating to", url)
    driver.get(url)
    time.sleep(6)
    
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    
    # Try to find anything that looks like an addon card
    # Usually they are inside a list or grid
    cards = soup.find_all("div", class_=lambda x: x and ("project-card" in x or "card" in x))
    if not cards:
        # Try links that start with /wow/addons/
        links = soup.find_all("a", href=lambda x: x and x.startswith("/wow/addons/") and not x.endswith("/files"))
        print(f"Found {len(links)} links to addons.")
        for a in links[:5]:
            print("Link:", a['href'], "Text:", a.text.strip())
    else:
        print(f"Found {len(cards)} cards")
        for card in cards[:3]:
            print(card.text[:100].strip())
            
    driver.quit()

if __name__ == "__main__":
    test()
