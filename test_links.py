import undetected_chromedriver as uc
import time
import json

options = uc.ChromeOptions()
options.headless = True # I will try headless, but it might fail. Let's just fetch all links if possible.
driver = uc.Chrome(options=options)

try:
    driver.get("https://www.curseforge.com/wow/search?class=addons&search=hero")
    time.sleep(5)
    
    js = """
    var arr = [];
    var links = document.querySelectorAll('a');
    for(var i=0; i<links.length; i++) {
        arr.push(links[i].href);
    }
    return arr;
    """
    links = driver.execute_script(js)
    with open("links.txt", "w") as f:
        for link in links:
            f.write(link + "\n")
    print("Links saved to links.txt")
except Exception as e:
    print("Failed:", e)
finally:
    driver.quit()
