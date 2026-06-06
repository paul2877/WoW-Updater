from bs4 import BeautifulSoup

with open("debug.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

cards = soup.find_all(class_=lambda c: c and "project-card" in c)
for card in cards[:3]:
    print("--- CARD ---")
    a_tags = card.find_all("a")
    for a in a_tags:
        print("A HREF:", a.get("href"))
        print("A TEXT:", repr(a.get_text(strip=True)))


