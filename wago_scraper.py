import requests
import urllib.parse
from threading import Thread

def search_wago(query):
    url = f"https://data.wago.io/search?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            hits = r.json().get('hits', [])
            results = []
            for hit in hits:
                # filter only weakauras
                if hit.get('type') != 'WEAKAURA':
                    continue
                results.append({
                    "id": hit.get("id"),
                    "slug": hit.get("slug") or hit.get("id"),
                    "name": hit.get("name"),
                    "author": hit.get("userName"),
                    "installs": hit.get("installs", 0),
                    "stars": hit.get("stars", 0),
                    "description": hit.get("descriptionSanitized") or hit.get("description") or "Нет описания."
                })
            return results
    except Exception as e:
        print(f"Error searching wago: {e}")
    return []

def extract_wago_string(wago_slug):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    import time
    
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    
    driver = None
    wago_string = None
    try:
        try:
            # 1. Пытаемся запустить Google Chrome
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
        except Exception as e_chrome:
            try:
                # 2. Если Хрома нет, пробуем встроенный Microsoft Edge
                from selenium.webdriver.edge.service import Service as EdgeService
                from selenium.webdriver.edge.options import Options as EdgeOptions
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                e_opts = EdgeOptions()
                e_opts.add_argument('--headless=new')
                e_opts.add_argument('--disable-gpu')
                e_opts.add_argument('--no-sandbox')
                e_opts.add_argument('--disable-dev-shm-usage')
                driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=e_opts)
            except Exception as e_edge:
                try:
                    # 3. Если и Edge удален, пробуем Firefox
                    from selenium.webdriver.firefox.service import Service as FirefoxService
                    from selenium.webdriver.firefox.options import Options as FirefoxOptions
                    from webdriver_manager.firefox import GeckoDriverManager
                    f_opts = FirefoxOptions()
                    f_opts.add_argument('-headless')
                    driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=f_opts)
                except Exception as e_firefox:
                    raise Exception("Не найден подходящий браузер (Chrome, Edge или Firefox). Установите один из них для загрузки Wago.")
        
        driver.get(f'https://wago.io/{wago_slug}')
        
        # Inject script to capture clipboard writes safely in headless mode
        driver.execute_script("""
            window.wagoString = null;
            Object.defineProperty(navigator, 'clipboard', {
                value: {
                    writeText: function(text) {
                        window.wagoString = text;
                        return Promise.resolve();
                    }
                },
                configurable: true
            });
            
            // Also override document.execCommand as fallback
            const originalExec = document.execCommand;
            document.execCommand = function(command, ui, value) {
                if(command === 'copy') {
                    // Try to get selection
                    const text = window.getSelection().toString();
                    if(text && text.includes('!WA:2!')) window.wagoString = text;
                }
                return originalExec.apply(document, arguments);
            };
        """)
        
        # Wait for Cloudflare to pass and page to load
        wait = WebDriverWait(driver, 15)
        
        try:
            # Find the copy button using ID instead of text (case-sensitive)
            btn = wait.until(EC.presence_of_element_located((By.ID, "copyImportBtn")))
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2) # wait for JS to execute copy
            
            wago_string = driver.execute_script("return window.wagoString;")
            if wago_string and wago_string.startswith("!WA:2!"):
                return wago_string
                
        except Exception as e:
            print(f"Error finding copy button: {e}")
            
    except Exception as e:
        print(f"Selenium error: {e}")
    finally:
        if driver:
            driver.quit()
            
    if not wago_string:
        import webbrowser
        webbrowser.open(f'https://wago.io/{wago_slug}')
        
    return wago_string
