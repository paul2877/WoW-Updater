import os
import json
import urllib.request
import zipfile
import shutil
import tempfile
import urllib.parse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

CONFIG_FILE = "config.json"
STATE_FILE = "local_state.json"
API_BASE = "https://api.curse.tools/v1/cf"

state_lock = threading.Lock()
config_lock = threading.Lock()
global_extract_lock = threading.Lock()
addon_locks = {}
addon_locks_lock = threading.Lock()

def get_addon_lock(addon_id):
    with addon_locks_lock:
        if addon_id not in addon_locks:
            addon_locks[addon_id] = threading.Lock()
        return addon_locks[addon_id]

def load_config():
    with config_lock:
        if not os.path.exists(CONFIG_FILE):
            return {
                "api_key": "",
                "addons_path": "",
                "game_version": "Retail (The War Within)",
                "addon_ids": []
            }
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            if "game_version" not in config:
                config["game_version"] = "Retail (The War Within)"
            return config

def save_config(config):
    with config_lock:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

def load_state():
    with state_lock:
        if not os.path.exists(STATE_FILE):
            return {}
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_state(state):
    with state_lock:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)

def api_request(url, api_key, retries=5, log_callback=None):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "x-api-key": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (401, 404):
                return None
            if log_callback: log_callback(f"[Debug] Ошибка {e.code} от CurseForge. Повтор через 2с... (Попытка {attempt+1}/{retries})")
            time.sleep(2)
        except Exception as e:
            if log_callback: log_callback(f"[Debug] Ошибка соединения. Повтор через 2с... (Попытка {attempt+1}/{retries})")
            time.sleep(2)
    return None

def search_addons(query, api_key=None, log_callback=None):
    if not api_key:
        config = load_config()
        api_key = config.get("api_key", "")
    url = f"{API_BASE}/mods/search?gameId=1&searchFilter={urllib.parse.quote(query)}&sortField=2&sortOrder=desc"
    data = api_request(url, api_key, log_callback=log_callback)
    if data and "data" in data:
        results = []
        for item in data["data"]:
            author = "Unknown"
            if item.get("authors") and len(item["authors"]) > 0:
                author = item["authors"][0].get("name", "Unknown")
            logoUrl = ""
            if item.get("logo"):
                logoUrl = item["logo"].get("thumbnailUrl", "")
            results.append({
                "id": item["id"],
                "name": item["name"],
                "author": author,
                "summary": item.get("summary", ""),
                "logoUrl": logoUrl,
                "downloadCount": item.get("downloadCount", 0),
                "slug": item.get("slug", "")
            })
            
        # Сначала точное совпадение по имени, затем сортировка по загрузкам
        q_lower = query.lower().strip()
        results.sort(key=lambda x: (
            0 if x["name"].lower() == q_lower else (1 if q_lower in x["name"].lower() else 2),
            -x["downloadCount"]
        ))
        
        return results, None
    return [], "Ничего не найдено или ошибка API."

def get_latest_file(addon_id, api_key, target_version=None, log_callback=None):
    game_version_type_id = 517 # Retail (по умолчанию)
    if target_version:
        if "Cataclysm" in target_version:
            game_version_type_id = 77522
        elif "Classic Era" in target_version:
            game_version_type_id = 67408
            
    url = f"{API_BASE}/mods/{addon_id}/files?gameVersionTypeId={game_version_type_id}"
    data = api_request(url, api_key, log_callback=log_callback)
    if not data or "data" not in data or not data["data"]:
        return None
        
    files = data["data"]
    target_version = str(target_version).strip()
    matching_files = []
    
    if target_version and target_version[0].isdigit():
        version_num = target_version.split(" ")[0]
        matching_files = [f for f in files if any(version_num == gv.get('gameVersionName', '') for gv in f.get('sortableGameVersions', []))]
        if not matching_files:
            matching_files = [f for f in files if any(version_num in gv.get('gameVersionName', '') for gv in f.get('sortableGameVersions', []))]

    if not matching_files:
        target_type_id = 517 
        if "Cataclysm" in target_version:
            target_type_id = 73246
        elif "Classic Era" in target_version:
            target_type_id = 67408
            
    # Сначала ищем строгое совпадение по строке версии (например "11.0.5")
    exact_matches = []
    if target_version:
        for f in files:
            for gv in f.get('sortableGameVersions', []):
                if target_version in gv.get('gameVersionName', ''):
                    exact_matches.append(f)
                    break
                    
    # Если строгих совпадений нет, ищем по target_type_id (со fallback логикой для Retail/Classic)
    matching_files = exact_matches
    if not matching_files:
        matching_files = [f for f in files if any(gv.get('gameVersionTypeId') == target_type_id for gv in f.get('sortableGameVersions', []))]
        
        if not matching_files:
            for f in files:
                for gv in f.get('sortableGameVersions', []):
                    name = gv.get('gameVersionName', '')
                    if target_type_id == 517 and ('11.' in name or '12.' in name):
                        matching_files.append(f)
                        break
                    if target_type_id == 73246 and ('4.4' in name or 'Cataclysm' in name):
                        matching_files.append(f)
                        break
                    if target_type_id == 67408 and ('1.15' in name or 'Classic' in name):
                        matching_files.append(f)
                        break

    if not matching_files:
        matching_files = files

    # Из подходящих выбираем релиз (1), если нет — бету (2), если нет — альфу (3)
    best_file = None
    for release_type in [1, 2, 3]:
        for f in matching_files:
            if f.get('releaseType') == release_type:
                best_file = f
                break
        if best_file:
            break

    if not best_file and matching_files:
        best_file = matching_files[0]
        
    return best_file

def get_addon_files(addon_id, api_key, log_callback=None):
    url = f"{API_BASE}/mods/{addon_id}/files?pageSize=200"
    data = api_request(url, api_key, log_callback=log_callback)
    if data and "data" in data:
        return data["data"]
    return []

def get_download_url(addon_id, file_id, api_key, log_callback=None):
    url = f"{API_BASE}/mods/{addon_id}/files/{file_id}/download-url"
    data = api_request(url, api_key, log_callback=log_callback)
    if data and "data" in data:
        return data["data"]
    return None

def get_mod_info(addon_id, api_key, log_callback=None):
    url = f"{API_BASE}/mods/{addon_id}"
    data = api_request(url, api_key, log_callback=log_callback)
    if data and "data" in data:
        return data["data"]
    return None

def get_numeric_id_from_slug(slug):
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    import time
    import re
    
    options = uc.ChromeOptions()
    options.headless = False
    driver = uc.Chrome(options=options)
    driver.get(f"https://www.curseforge.com{slug}")
    time.sleep(5)
    
    html = driver.page_source
    driver.quit()
    
    # Ищем Project ID: 256782
    match = re.search(r"Project ID.*?(\d{4,8})", html, re.IGNORECASE | re.DOTALL)
    if match:
        return int(match.group(1))
    
    # Fallback: ищем в мета-тегах или других местах
    match = re.search(r"curseforge:projectId\"\s+content=\"(\d+)\"", html, re.IGNORECASE)
    if match:
        return int(match.group(1))
        
    return None

def download_and_extract(url, target_dir, progress_callback=None):
    with global_extract_lock:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.getheader('Content-Length', 0))
                downloaded = 0
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        tmp.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
                    tmp_path = tmp.name
                    
            extracted_folders = []
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                for info in zip_ref.infolist():
                    extracted_path = zip_ref.extract(info, target_dir)
                    parts = info.filename.replace('\\', '/').split('/')
                    if len(parts) > 0 and parts[0]:
                        if parts[0] not in extracted_folders:
                            extracted_folders.append(parts[0])
                            
            os.remove(tmp_path)
            return True, extracted_folders
        except Exception as e:
            return False, []

def install_addon(addon_id, log_callback=None, installed_list=None, override_path=None, progress_callback=None, force_reinstall=False, target_file_id=None):
    with get_addon_lock(addon_id):
        return _install_addon_locked(addon_id, log_callback, installed_list, override_path, progress_callback, force_reinstall, target_file_id)

def _install_addon_locked(addon_id, log_callback=None, installed_list=None, override_path=None, progress_callback=None, force_reinstall=False, target_file_id=None):
    if installed_list is None:
        installed_list = []
    
    config = load_config()
    
    # Если передан текстовый URL (slug из поиска), находим его числовой ID
    if isinstance(addon_id, str) and addon_id.startswith("/wow/addons/"):
        if log_callback: log_callback(f"Определяем ID для {addon_id}...")
        numeric_id = get_numeric_id_from_slug(addon_id)
        if not numeric_id:
            if log_callback: log_callback(f"Ошибка: Не удалось найти числовой ID для {addon_id}")
            return False
        addon_id = numeric_id
        
    if addon_id in installed_list and not force_reinstall:
        return True # Уже обработан в этой сессии

    installed_list.append(addon_id)
    
    config = load_config()
    api_key = config.get("api_key", "")
    addons_path = override_path if override_path else config.get("addons_path", "")
    
    if log_callback: log_callback(f"Получение информации об аддоне {addon_id}...")
    mod_info = get_mod_info(addon_id, api_key, log_callback=log_callback)
    
    if not api_key or not addons_path:
        if log_callback: log_callback("Ошибка: не задан API ключ или путь к WoW в настройках.")
        return False

    if not os.path.exists(addons_path):
        os.makedirs(addons_path, exist_ok=True)

    mod_name = mod_info["name"] if mod_info else str(addon_id)
    logo_url = ""
    if mod_info and "logo" in mod_info and mod_info["logo"]:
        logo_url = mod_info["logo"].get("thumbnailUrl", "")

    # Раннее сохранение в стейт, чтобы иконки подтянулись даже если апдейт заблокирован
    state = load_state()
    addon_id_str = str(addon_id)
    if isinstance(state.get(addon_id_str), dict):
        if state[addon_id_str].get("name") != mod_name or state[addon_id_str].get("logoUrl") != logo_url:
            state[addon_id_str]["name"] = mod_name
            state[addon_id_str]["logoUrl"] = logo_url
            save_state(state)
    elif state.get(addon_id_str):
        state[addon_id_str] = {
            "file_id": state[addon_id_str],
            "name": mod_name,
            "logoUrl": logo_url,
            "folders": []
        }
        save_state(state)
    else:
        state[addon_id_str] = {
            "file_id": None,
            "name": mod_name,
            "logoUrl": logo_url,
            "folders": []
        }
        save_state(state)

    if log_callback: log_callback(f"Проверка {mod_name} (ID: {addon_id})...")
    
    if target_file_id:
        url = f"{API_BASE}/mods/{addon_id}/files/{target_file_id}"
        data = api_request(url, api_key, log_callback=log_callback)
        if not data or "data" not in data:
            if log_callback: log_callback(f"[-] Не удалось получить файл с ID {target_file_id}.")
            return False
        latest_file = data["data"]
    else:
        target_version = config.get("game_version", "Retail (The War Within)")
        latest_file = get_latest_file(addon_id, api_key, target_version=target_version, log_callback=log_callback)
    
    if not latest_file:
        if log_callback: log_callback(f"[-] Нет файлов для скачивания ({mod_name}).")
        return False
        
    file_id = str(latest_file["id"])
    file_name = latest_file["fileName"]
    download_url = latest_file.get("downloadUrl")
    
    if not download_url:
        download_url = get_download_url(addon_id, file_id, api_key, log_callback=log_callback)
        
    if not download_url:
        if log_callback: log_callback(f"[-] CurseForge заблокировал скачивание {mod_name} (требует офф. клиент).")
        return False

    # Check dependencies first!
    deps = latest_file.get("dependencies", [])
    required_deps = [d["modId"] for d in deps if d.get("relationType") == 3 and "modId" in d]
    for dep_id in required_deps:
        if log_callback: log_callback(f"Найдена зависимость ID: {dep_id} для {mod_name}. Устанавливаем...")
        install_addon(dep_id, log_callback, installed_list, override_path, progress_callback, force_reinstall)
        
    state = load_state()
    addon_id_str = str(addon_id)
    
    if isinstance(state.get(addon_id_str), dict):
        current_file_id = state[addon_id_str].get("file_id")
        if state[addon_id_str].get("name") != mod_name or state[addon_id_str].get("logoUrl") != logo_url:
            state[addon_id_str]["name"] = mod_name
            state[addon_id_str]["logoUrl"] = logo_url
            save_state(state)
    else:
        current_file_id = state.get(addon_id_str)
        if current_file_id:
            state[addon_id_str] = {
                "file_id": current_file_id,
                "name": mod_name,
                "logoUrl": logo_url,
                "folders": []
            }
            save_state(state)
    folders_exist = True
    if state.get(addon_id_str) and state[addon_id_str].get("folders"):
        for folder_name in state[addon_id_str]["folders"]:
            if not os.path.exists(os.path.join(addons_path, folder_name)):
                folders_exist = False
                break
    else:
        folders_exist = False
        
    if current_file_id == file_id and not override_path and folders_exist and not force_reinstall:
        if log_callback: log_callback(f"[OK] {mod_name} уже актуален ({file_name}).")
    else:
        if log_callback: log_callback(f"Скачивание {mod_name} ({file_name})...")
        
        # Очистка старых папок перед переустановкой/обновлением
        if state.get(addon_id_str) and state[addon_id_str].get("folders"):
            for folder_name in state[addon_id_str]["folders"]:
                folder_path = os.path.join(addons_path, folder_name)
                if os.path.exists(folder_path):
                    try:
                        shutil.rmtree(folder_path)
                    except Exception as e:
                        if log_callback: log_callback(f"[-] Не удалось удалить старую папку {folder_name}: {e}")
        
        success, extracted_folders = download_and_extract(download_url, addons_path, progress_callback=progress_callback)
        if success:
            state[addon_id_str] = {
                "file_id": file_id,
                "name": mod_name,
                "logoUrl": logo_url,
                "folders": extracted_folders
            }
            save_state(state)
            if log_callback: log_callback(f"[+] Успешно установлен/обновлен {mod_name}.")
        else:
            if log_callback: log_callback(f"[-] Ошибка при установке {mod_name}.")
            return False
            
    # Add to config if not present
    if addon_id not in config["addon_ids"]:
        config["addon_ids"].append(addon_id)
        save_config(config)

    return True

def update_all(log_callback=None, progress_callback_factory=None):
    if log_callback: log_callback("Сканирование папки перед обновлением...")
    added, _ = scan_local_addons(log_callback=log_callback)
    if added > 0 and log_callback:
        log_callback(f"Добавлено новых аддонов: {added}")
        
    config = load_config()
    addon_ids = config.get("addon_ids", [])
    if not addon_ids:
        if log_callback: log_callback("Список аддонов пуст.")
        return
        
    for aid in addon_ids:
        try:
            cb = progress_callback_factory(aid) if progress_callback_factory else None
            install_addon(aid, log_callback=log_callback, progress_callback=cb)
            time.sleep(1)
        except Exception as e:
            if log_callback: log_callback(f"[-] Внутренняя ошибка при обновлении: {e}")
    
    if log_callback: log_callback("Обновление завершено!")

def import_addons(source_path, log_callback=None):
    config = load_config()
    target_path = config.get("addons_path", "")
    
    if not target_path or not os.path.exists(target_path):
        if log_callback: log_callback("Ошибка: В настройках не указана или не существует целевая папка WoW AddOns.")
        return

    source_abs = os.path.abspath(source_path).lower()
    target_abs = os.path.abspath(target_path).lower()
    
    if source_abs == target_abs:
        if log_callback: log_callback("Исходная и целевая папки совпадают. Копирование пропущено, запускаем сканирование установленных аддонов...")
    elif os.path.exists(source_path):
        import shutil
        success_count = 0
        error_count = 0
        
        for item in os.listdir(source_path):
            s = os.path.join(source_path, item)
            d = os.path.join(target_path, item)
            try:
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    os.makedirs(target_path, exist_ok=True)
                    shutil.copy2(s, d)
                success_count += 1
            except Exception as e:
                if log_callback: log_callback(f"Ошибка копирования {item}: {e}")
                error_count += 1
                
        if log_callback: log_callback(f"Копирование папок завершено. Успешно: {success_count}, Ошибок: {error_count}.")
        if log_callback: log_callback("Приступаем к загрузке свежих версий...")
    else:
        if log_callback: log_callback(f"Папка {source_path} не существует. Пропускаем копирование.")
            
    # Сначала просканируем целевую папку, чтобы точно найти всё, что можно обновить
    scan_local_addons(log_callback=None)
    
    # Загрузим свежий конфиг после сканирования
    config = load_config()
    addon_ids = config.get("addon_ids", [])
    
    if not addon_ids:
        if log_callback: log_callback("Нет известных аддонов для обновления с CurseForge.")
        return
        
    for aid in addon_ids:
        try:
            install_addon(aid, log_callback=log_callback, override_path=target_path)
            time.sleep(1)
        except Exception as e:
            if log_callback: log_callback(f"[-] Внутренняя ошибка при импорте: {e}")
        
    if log_callback: log_callback("Импорт и актуализация успешно завершены!")

def scan_local_addons(log_callback=None):
    config = load_config()
    addons_path = config.get("addons_path", "")
    if not os.path.exists(addons_path):
        return 0
    
    found_ids = set()
    for item in os.listdir(addons_path):
        folder_path = os.path.join(addons_path, item)
        if os.path.isdir(folder_path):
            toc_path = os.path.join(folder_path, f"{item}.toc")
            if os.path.exists(toc_path):
                try:
                    with open(toc_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line_lower = line.lower()
                            if "x-curse-project-id:" in line_lower:
                                project_id = line_lower.split("x-curse-project-id:")[1].strip()
                                if project_id.isdigit():
                                    found_ids.add(int(project_id))
                                break
                except:
                    pass
                    
    added_count = 0
    addon_ids = config.get("addon_ids", [])
    for aid in found_ids:
        if aid not in addon_ids:
            addon_ids.append(aid)
            added_count += 1
            
    if added_count > 0:
        config["addon_ids"] = addon_ids
        save_config(config)
        
    return added_count

def get_installed_addons():
    config = load_config()
    state = load_state()
    
    results = []
    for aid in config.get("addon_ids", []):
        aid_str = str(aid)
        info = state.get(aid_str)
        name = f"Unknown Addon (ID: {aid})"
        logo_url = ""
        if isinstance(info, dict):
            name = info.get("name", name)
            logo_url = info.get("logoUrl", "")
        results.append({"id": aid, "name": name, "logoUrl": logo_url})
    return results

def get_unmanaged_addons():
    config = load_config()
    state = load_state()
    addons_path = config.get("addons_path", "")
    
    if not os.path.exists(addons_path):
        return []
        
    managed_folders = set()
    for aid_str, info in state.items():
        if isinstance(info, dict) and "folders" in info:
            for f in info["folders"]:
                managed_folders.add(f.lower())
                
    unmanaged = []
    for item in os.listdir(addons_path):
        folder_path = os.path.join(addons_path, item)
        if os.path.isdir(folder_path) and item.lower() not in managed_folders:
            toc_path = os.path.join(folder_path, f"{item}.toc")
            if os.path.exists(toc_path):
                unmanaged.append({"id": item, "name": f"{item} (Локальный)", "logoUrl": ""})
                
    return unmanaged

def uninstall_addon(addon_id, log_callback=None):
    config = load_config()
    state = load_state()
    addons_path = config.get("addons_path", "")
    
    aid_str = str(addon_id)
    info = state.get(aid_str)
    
    name = f"ID: {addon_id}"
    
    if isinstance(info, dict):
        name = info.get("name", name)
        folders = info.get("folders", [])
        for folder in folders:
            folder_path = os.path.join(addons_path, folder)
            if os.path.exists(folder_path):
                try:
                    shutil.rmtree(folder_path)
                    if log_callback: log_callback(f"Удалена папка: {folder}")
                except Exception as e:
                    if log_callback: log_callback(f"Ошибка удаления {folder}: {e}")
                    
    if aid_str in state:
        del state[aid_str]
        save_state(state)
        
    addon_ids = config.get("addon_ids", [])
    if addon_id in addon_ids:
        addon_ids.remove(addon_id)
        config["addon_ids"] = addon_ids
        save_config(config)
        
    if log_callback: log_callback(f"[+] Аддон {name} успешно удален.")

def uninstall_unmanaged_addon(folder_name, log_callback=None):
    config = load_config()
    addons_path = config.get("addons_path", "")
    target = os.path.join(addons_path, folder_name)
    if os.path.exists(target):
        try:
            import shutil
            shutil.rmtree(target)
            if log_callback: log_callback(f"[+] Локальная папка {folder_name} удалена.")
        except Exception as e:
            if log_callback: log_callback(f"[-] Ошибка удаления {folder_name}: {e}")

def export_addon_list(filepath, log_callback=None):
    config = load_config()
    state = load_state()
    addon_ids = config.get("addon_ids", [])
    
    export_data = {
        "format_version": 1,
        "addons": []
    }
    
    for aid in addon_ids:
        aid_str = str(aid)
        info = state.get(aid_str, {})
        name = info.get("name", f"Unknown Addon (ID: {aid})") if isinstance(info, dict) else f"Unknown Addon (ID: {aid})"
        export_data["addons"].append({
            "id": aid,
            "name": name
        })
        
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=4, ensure_ascii=False)
        if log_callback: log_callback(f"Список успешно сохранен в {filepath}")
        return True
    except Exception as e:
        if log_callback: log_callback(f"Ошибка при импорте списка: {e}")
        return False

def import_addon_list(filepath, log_callback=None):
    if not os.path.exists(filepath):
        if log_callback: log_callback(f"Файл {filepath} не найден.")
        return False
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        if log_callback: log_callback(f"Ошибка чтения файла списка: {e}")
        return False
        
    addons = data.get("addons", [])
    if not addons:
        if log_callback: log_callback("Файл списка пуст или имеет неверный формат.")
        return False
        
    config = load_config()
    current_ids = config.get("addon_ids", [])
    
    added_count = 0
    ids_to_install = []
    
    for item in addons:
        aid = item.get("id")
        if aid and aid not in current_ids:
            current_ids.append(aid)
            added_count += 1
        if aid:
            ids_to_install.append(aid)
            
    if added_count > 0:
        config["addon_ids"] = current_ids
        save_config(config)
        
    if log_callback: log_callback(f"Импорт завершен. Найдено {len(ids_to_install)} аддонов ({added_count} новых). Начинаем скачивание...")
    
    for aid in ids_to_install:
        install_addon(aid, log_callback)
        
    if log_callback: log_callback("Все аддоны из списка успешно установлены!")
    return True

def scan_local_addons(log_callback=None):
    config = load_config()
    api_key = config.get("api_key")
    addons_path = config.get("addons_path", "")
    
    if not addons_path or not os.path.exists(addons_path):
        if log_callback: log_callback("[-] Папка AddOns не найдена.")
        return 0, 0
        
    state = load_state()
    addon_ids = config.get("addon_ids", [])
    
    managed_folders = set()
    for aid in addon_ids:
        info = state.get(str(aid), {})
        if isinstance(info, dict):
            managed_folders.update(info.get("folders", []))
            
    found_unmanaged = []
    
    for folder_name in os.listdir(addons_path):
        folder_path = os.path.join(addons_path, folder_name)
        if not os.path.isdir(folder_path): continue
        if folder_name in managed_folders: continue
        if folder_name.startswith("Blizzard_"): continue
        
        toc_path = os.path.join(folder_path, f"{folder_name}.toc")
        if not os.path.exists(toc_path):
            toc_files = [f for f in os.listdir(folder_path) if f.endswith(".toc")]
            if toc_files:
                toc_path = os.path.join(folder_path, toc_files[0])
            else:
                continue
                
        try:
            with open(toc_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except:
            continue
            
        import re
        match = re.search(r"## X-Curse-Project-ID:\s*(\d+)", content)
        if match:
            project_id = int(match.group(1))
            if project_id not in addon_ids:
                found_unmanaged.append({"folder": folder_name, "id": project_id})
                continue
                
        title_match = re.search(r"## Title.*?:\s*(.+)", content)
        title = title_match.group(1).strip() if title_match else folder_name
        title = re.sub(r"\|c[0-9a-fA-F]{8}", "", title)
        title = title.replace("|r", "")
        
        found_unmanaged.append({"folder": folder_name, "title": title})
        
    if not found_unmanaged:
        if log_callback: log_callback("[i] Все локальные аддоны уже добавлены или это системные аддоны Blizzard.")
        return 0, 0
        
    if log_callback: log_callback(f"[*] Найдено {len(found_unmanaged)} неуправляемых локальных папок. Распознавание...")
    
    recognized_count = 0
    for item in found_unmanaged:
        if "id" in item:
            aid = item["id"]
            if aid not in addon_ids:
                url = f"{API_BASE}/mods/{aid}"
                data = api_request(url, api_key)
                if data and "data" in data:
                    mod_name = data["data"]["name"]
                    addon_ids.append(aid)
                    state[str(aid)] = {"name": mod_name, "folders": [item["folder"]]}
                    recognized_count += 1
                    if log_callback: log_callback(f"[+] Распознан по ID: {mod_name} (ID: {aid})")
        else:
            title = item["title"]
            results, _ = search_addons(title, api_key)
            if results:
                matched = False
                for res in results:
                    if res["name"].lower() == title.lower() or res["slug"].lower() == item["folder"].lower():
                        aid = res["id"]
                        if aid not in addon_ids:
                            addon_ids.append(aid)
                            state[str(aid)] = {"name": res["name"], "folders": [item["folder"]]}
                            recognized_count += 1
                            if log_callback: log_callback(f"[+] Распознан по имени: {res['name']} (ID: {aid})")
                        matched = True
                        break
                if not matched:
                    res = results[0]
                    if title.lower() in res["name"].lower():
                        aid = res["id"]
                        if aid not in addon_ids:
                            addon_ids.append(aid)
                            state[str(aid)] = {"name": res["name"], "folders": [item["folder"]]}
                            recognized_count += 1
                            if log_callback: log_callback(f"[+] Распознан примерно: {res['name']} (ID: {aid})")
            else:
                if log_callback: log_callback(f"[-] Не удалось найти аддон '{title}' на CurseForge.")
                
    config["addon_ids"] = addon_ids
    save_config(config)
    save_state(state)
    
    return len(found_unmanaged), recognized_count



def backup_wtf(target_zip_path, log_callback=None):
    config = load_config()
    addons_path = get_wow_addons_path()
    if not addons_path:
        if log_callback: log_callback("[-] Путь к игре не настроен.")
        return False
        
    wtf_path = os.path.join(os.path.dirname(os.path.dirname(addons_path)), "WTF")
    if not os.path.exists(wtf_path):
        if log_callback: log_callback("[-] Папка WTF не найдена.")
        return False
        
    try:
        import zipfile
        if log_callback: log_callback(f"[*] Создание резервной копии WTF...")
        with zipfile.ZipFile(target_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(wtf_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(wtf_path))
                    zipf.write(file_path, arcname)
        if log_callback: log_callback(f"[+] Бэкап успешно сохранен в {target_zip_path}")
        return True
    except Exception as e:
        if log_callback: log_callback(f"[-] Ошибка при создании бэкапа: {e}")
        return False



def switch_profile(new_profile_name, log_callback=None, progress_callback_factory=None):
    config = load_config()
    current_profile = config.get("current_profile", "Default")
    profiles = config.get("profiles", {"Default": config.get("addon_ids", [])})
    
    # Сохраняем текущий
    profiles[current_profile] = config.get("addon_ids", [])
    
    if new_profile_name not in profiles:
        profiles[new_profile_name] = []
        
    old_ids = set(profiles[current_profile])
    new_ids = set(profiles[new_profile_name])
    
    to_remove = old_ids - new_ids
    to_install = new_ids - old_ids
    
    if log_callback: log_callback(f"\n--- Переключение на профиль: {new_profile_name} ---")
    
    for aid in to_remove:
        uninstall_addon(aid, log_callback=log_callback)
        
    for aid in to_install:
        cb = progress_callback_factory(aid) if progress_callback_factory else None
        install_addon(aid, log_callback=log_callback, progress_callback=cb)
        
    config["current_profile"] = new_profile_name
    config["profiles"] = profiles
    config["addon_ids"] = list(new_ids)
    save_config(config)
    
    if log_callback: log_callback(f"[*] Профиль успешно переключен на {new_profile_name}")

def get_profiles():
    config = load_config()
    profiles = config.get("profiles", {"Default": config.get("addon_ids", [])})
    current = config.get("current_profile", "Default")
    return list(profiles.keys()), current
