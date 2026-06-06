import undetected_chromedriver as uc
import time
import json

def test():
    options = uc.ChromeOptions()
    options.headless = True
    driver = uc.Chrome(options=options)
    
    print("Navigating to main page...")
    driver.get("https://www.curseforge.com/wow/addons")
    time.sleep(5)
    
    print("Injecting fetch...")
    js = """
    var callback = arguments[arguments.length - 1];
    fetch('/api/v1/mods/search?gameId=1&classId=6&searchFilter=hero&sortField=2&pageSize=50')
      .then(r => r.text())
      .then(text => callback(text))
      .catch(e => callback("Error: " + e.toString()));
    """
    
    try:
        result = driver.execute_async_script(js)
        print("Fetch result length:", len(result))
        print("Snippet:", result[:200])
    except Exception as e:
        print("Script failed:", e)
        
    driver.quit()

if __name__ == "__main__":
    test()
