from bs4 import BeautifulSoup

with open("debug.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

cards = soup.find_all(class_=lambda c: c and "project-card" in c)
for card in cards[:1]:
    print("--- CARD ELEMENTS ---")
    for elem in card.descendants:
        if elem.name:
            print(f"TAG: {elem.name}, CLASSES: {elem.get('class', [])}")
            if elem.string:
                print(f"TEXT: {elem.string.strip()}")

