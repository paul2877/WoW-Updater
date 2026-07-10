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
                "downloadCount": item.get("downloadCount", 0)
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
    
    # Если юзер ввел конкретный патч цифрами (например "11.0.5 (The War Within)" или "11.1.0")
    if target_version and target_version[0].isdigit():
        version_num = target_version.split(" ")[0]
        for f in files:
            for gv in f.get('sortableGameVersions', []):
                if version_num == gv.get('gameVersionName', ''):
                    return f
        # Если точное совпадение не найдено, ищем частичное
        for f in files:
            for gv in f.get('sortableGameVersions', []):
                if version_num in gv.get('gameVersionName', ''):
                    return f

    # Идентификаторы версий игр на CurseForge
    # 517 = Retail
    # 73246 = Cataclysm Classic
    # 67408 = Classic Era
    
    target_type_id = 517 
    if "Cataclysm" in target_version:
        target_type_id = 73246
    elif "Classic Era" in target_version:
        target_type_id = 67408

    # Сначала пытаемся найти точное совпадение по type_id
    for f in files:
        for gv in f.get('sortableGameVersions', []):
            if gv.get('gameVersionTypeId') == target_type_id:
                return f
                
    # Fallback (ищем по строковому названию в имени версии, если type_id не подошел)
    for f in files:
        for gv in f.get('sortableGameVersions', []):
            name = gv.get('gameVersionName', '')
            if target_type_id == 517 and ('11.' in name or '12.' in name):
                return f
            if target_type_id == 73246 and ('4.4' in name or 'Cataclysm' in name):
                return f
            if target_type_id == 67408 and ('1.15' in name or 'Classic' in name):
                return f
                
    # Если вообще ничего не нашли, возвращаем самый последний файл
    return files[0]

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

def download_and_extract(url, target_dir):
    with global_extract_lock:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                    shutil.copyfileobj(response, tmp)
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

def install_addon(addon_id, log_callback=None, installed_list=None, override_path=None):
    with get_addon_lock(addon_id):
        return _install_addon_locked(addon_id, log_callback, installed_list, override_path)

def _install_addon_locked(addon_id, log_callback=None, installed_list=None, override_path=None):
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
        
    if addon_id in installed_list:
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
    
    target_version = config.get("game_version", "Retail (The War Within)")
    latest_file = get_latest_file(addon_id, api_key, target_version=target_version, log_callback=log_callback)
    if not latest_file:
        if log_callback: log_callback(f"[-] Нет файлов для версии {target_version} ({mod_name}).")
        return False
        
    file_id = str(latest_file["id"])
    file_name = latest_file["fileName"]
    download_url = latest_file.get("downloadUrl")
    
    if not download_url:
        download_url = get_download_url(addon_id, file_id, api_key, log_callback=log_callback)
        
    if not download_url:
        if log_callback: log_callback(f"[!] API не отдал ссылку для {mod_name}. Пробуем собрать её вручную...")
        # Реконструируем URL для edge.forgecdn.net
        if len(file_id) >= 7:
            part1 = file_id[:4]
            part2 = file_id[4:]
            download_url = f"https://edge.forgecdn.net/files/{part1}/{part2}/{urllib.parse.quote(file_name)}"
        elif len(file_id) == 6:
            part1 = file_id[:3]
            part2 = file_id[3:]
            download_url = f"https://edge.forgecdn.net/files/{part1}/{part2}/{urllib.parse.quote(file_name)}"
            
    if not download_url:
        if log_callback: log_callback(f"[-] Не удалось получить ссылку для {mod_name}.")
        return False

    # Check dependencies first!
    deps = latest_file.get("dependencies", [])
    required_deps = [d["modId"] for d in deps if d.get("relationType") == 3 and "modId" in d]
    for dep_id in required_deps:
        if log_callback: log_callback(f"Найдена зависимость ID: {dep_id} для {mod_name}. Устанавливаем...")
        install_addon(dep_id, log_callback, installed_list, override_path)
        
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
        
    if current_file_id == file_id and not override_path and folders_exist:
        if log_callback: log_callback(f"[OK] {mod_name} уже актуален ({file_name}).")
    else:
        if log_callback: log_callback(f"Скачивание {mod_name} ({file_name})...")
        success, extracted_folders = download_and_extract(download_url, addons_path)
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

def update_all(log_callback=None):
    if log_callback: log_callback("Сканирование папки перед обновлением...")
    added = scan_local_addons(log_callback=log_callback)
    if added > 0 and log_callback:
        log_callback(f"Добавлено новых аддонов: {added}")
        
    config = load_config()
    addon_ids = config.get("addon_ids", [])
    if not addon_ids:
        if log_callback: log_callback("Список аддонов пуст.")
        return
        
    for aid in addon_ids:
        try:
            install_addon(aid, log_callback=log_callback)
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
        if log_callback: log_callback(f"Ошибка сохранения списка: {e}")
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


import customtkinter as ctk
import threading

import io
import os
import hashlib
import urllib.request
import tempfile
try:
    from PIL import Image
except ImportError:
    pass

class ImageLoader:
    def __init__(self):
        self.cache = {}
        self.icons_dir = os.path.join(tempfile.gettempdir(), "wow_updater_icons")
        if not os.path.exists(self.icons_dir):
            os.makedirs(self.icons_dir)
        
    def get_image(self, url, size=(50, 50), callback=None):
        if not url: return None
        if url in self.cache:
            if callback: callback(self.cache[url])
            return self.cache[url]
            
        def download():
            try:
                filename = hashlib.md5(url.encode('utf-8')).hexdigest() + ".png"
                filepath = os.path.join(self.icons_dir, filename)
                
                if os.path.exists(filepath):
                    img = Image.open(filepath)
                else:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = resp.read()
                    img = Image.open(io.BytesIO(data))
                    img.save(filepath, format="PNG")
                    
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                self.cache[url] = ctk_img
                if callback: callback(ctk_img)
            except Exception as e:
                pass
                
        threading.Thread(target=download, daemon=True).start()
        return None

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WoW Updater (CurseForge Style)")
        self.geometry("950x650")
        try:
            import sys
            bundle_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
            icon_path = os.path.join(bundle_dir, "app.ico")
            self.iconbitmap(icon_path)
        except Exception:
            pass
        self.configure(fg_color="#121216")
        self.image_loader = ImageLoader()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#1A1A1D")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="WoW Updater", font=ctk.CTkFont(size=20, weight="bold"), text_color="#F45821")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        self.btn_nav_installed = ctk.CTkButton(self.sidebar_frame, text="Мои аддоны", fg_color="transparent", text_color=("gray10", "gray90"), hover_color="#25252B", anchor="w", command=self.show_installed)
        self.btn_nav_installed.grid(row=1, column=0, pady=5, padx=10, sticky="ew")

        self.btn_nav_search = ctk.CTkButton(self.sidebar_frame, text="Поиск", fg_color="transparent", text_color=("gray10", "gray90"), hover_color="#25252B", anchor="w", command=self.show_search)
        self.btn_nav_search.grid(row=2, column=0, pady=5, padx=10, sticky="ew")

        self.btn_nav_settings = ctk.CTkButton(self.sidebar_frame, text="Настройки", fg_color="transparent", text_color=("gray10", "gray90"), hover_color="#25252B", anchor="w", command=self.show_settings)
        self.btn_nav_settings.grid(row=3, column=0, pady=5, padx=10, sticky="ew")

        self.lbl_copyright = ctk.CTkLabel(self.sidebar_frame, text="© angeldev", font=ctk.CTkFont(size=11), text_color="gray40")
        self.lbl_copyright.grid(row=5, column=0, pady=20, sticky="s")

        # Main Content Frames
        self.frame_installed = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.frame_search = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.frame_settings = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)

        self.setup_settings_tab()
        self.setup_search_tab()
        self.setup_installed_tab()
        self.setup_bindings()

        self.load_settings()
        self.show_installed()
        self.refresh_installed_list()

    def select_nav_button(self, name):
        self.btn_nav_installed.configure(fg_color="#F45821" if name == "installed" else "transparent")
        self.btn_nav_search.configure(fg_color="#F45821" if name == "search" else "transparent")
        self.btn_nav_settings.configure(fg_color="#F45821" if name == "settings" else "transparent")

    def show_installed(self):
        self.select_nav_button("installed")
        self.frame_search.grid_forget()
        self.frame_settings.grid_forget()
        self.frame_installed.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_search(self):
        self.select_nav_button("search")
        self.frame_installed.grid_forget()
        self.frame_settings.grid_forget()
        self.frame_search.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_settings(self):
        self.select_nav_button("settings")
        self.frame_installed.grid_forget()
        self.frame_search.grid_forget()
        self.frame_settings.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def setup_settings_tab(self):
        self.lbl_api = ctk.CTkLabel(self.frame_settings, text="CurseForge API Key:")
        self.lbl_api.pack(pady=(10, 5), padx=20, anchor="w")
        
        api_frame = ctk.CTkFrame(self.frame_settings, fg_color="transparent")
        api_frame.pack(pady=5, padx=20, anchor="w", fill="x")
        
        self.entry_api = ctk.CTkEntry(api_frame, width=450)
        self.entry_api.pack(side="left", padx=(0, 10))
        
        self.btn_api_file = ctk.CTkButton(api_frame, text="📄 Из файла", width=80, command=self.do_load_api_file)
        self.btn_api_file.pack(side="left")

        self.lbl_path = ctk.CTkLabel(self.frame_settings, text="Путь к WoW AddOns:")
        self.lbl_path.pack(pady=(20, 5), padx=20, anchor="w")
        
        path_frame = ctk.CTkFrame(self.frame_settings, fg_color="transparent")
        path_frame.pack(pady=5, padx=20, anchor="w", fill="x")
        
        self.entry_path = ctk.CTkEntry(path_frame, width=450)
        self.entry_path.pack(side="left", padx=(0, 10))
        
        self.btn_browse = ctk.CTkButton(path_frame, text="📁 Обзор", width=80, command=self.do_browse_path)
        self.btn_browse.pack(side="left")
        
        self.lbl_version = ctk.CTkLabel(self.frame_settings, text="Версия игры (выберите из списка ИЛИ впишите патч вручную, напр. 11.0.5):")
        self.lbl_version.pack(pady=(20, 5), padx=20, anchor="w")
        self.option_version = ctk.CTkComboBox(self.frame_settings, values=[
            "11.0.0 (The War Within)", 
            "11.0.2 (The War Within)", 
            "11.0.5 (The War Within)", 
            "11.0.7 (The War Within)", 
            "11.1.0 (The War Within)", 
            "12.0.0 (Midnight)", 
            "Cataclysm Classic", 
            "Classic Era"
        ], width=300)
        self.option_version.pack(pady=5, padx=20, anchor="w")

        self.btn_save = ctk.CTkButton(self.frame_settings, text="Сохранить настройки", command=self.save_settings)
        self.btn_save.pack(pady=30, padx=20, anchor="w")

        self.lbl_status = ctk.CTkLabel(self.frame_settings, text="", text_color="green")
        self.lbl_status.pack(pady=5, padx=20, anchor="w")

    def setup_search_tab(self):
        frame_top = ctk.CTkFrame(self.frame_search, fg_color="transparent")
        frame_top.pack(fill="x", padx=10, pady=10)

        self.entry_search = ctk.CTkEntry(frame_top, placeholder_text="Название аддона...", width=400)
        self.entry_search.pack(side="left", padx=(0, 10))

        self.btn_search = ctk.CTkButton(frame_top, text="Найти", fg_color="#F45821", hover_color="#FF7243", command=self.do_search)
        self.btn_search.pack(side="left")

        self.scroll_search = ctk.CTkScrollableFrame(self.frame_search)
        self.scroll_search.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_installed_tab(self):
        frame_top = ctk.CTkFrame(self.frame_installed, fg_color="transparent")
        frame_top.pack(fill="x", padx=10, pady=(10, 0))

        self.btn_update = ctk.CTkButton(frame_top, text="Обновить всё", fg_color="#F45821", hover_color="#FF7243", command=self.do_update_all)
        self.btn_update.pack(side="left", padx=(0, 10))

        self.btn_reinstall_all = ctk.CTkButton(frame_top, text="Переустановить всё", fg_color="#C2185B", hover_color="#AD1457", command=self.do_reinstall_all)
        self.btn_reinstall_all.pack(side="left", padx=(0, 10))
        
        self.btn_export = ctk.CTkButton(frame_top, text="Клонировать сборку", fg_color="#F57C00", hover_color="#E65100", command=self.do_import)
        self.btn_export.pack(side="left", padx=(0, 10))

        self.btn_export_list = ctk.CTkButton(frame_top, text="Сохранить список", fg_color="#1976D2", hover_color="#1565C0", command=self.do_export_list)
        self.btn_export_list.pack(side="left", padx=(0, 10))
        
        self.btn_import_list = ctk.CTkButton(frame_top, text="Загрузить из списка", fg_color="#388E3C", hover_color="#2E7D32", command=self.do_import_list)
        self.btn_import_list.pack(side="left")

        frame_filter = ctk.CTkFrame(self.frame_installed, fg_color="transparent")
        frame_filter.pack(fill="x", padx=10, pady=(10, 0))

        self.var_filter = ctk.StringVar()
        self.var_filter.trace_add("write", lambda *args: self.refresh_installed_list())
        
        self.entry_filter = ctk.CTkEntry(frame_filter, placeholder_text="Поиск по установленным аддонам...", textvariable=self.var_filter, corner_radius=15)
        self.entry_filter.pack(fill="x")

        self.scroll_installed = ctk.CTkScrollableFrame(self.frame_installed, height=250)
        self.scroll_installed.pack(fill="both", expand=True, padx=10, pady=10)

        self.textbox_log = ctk.CTkTextbox(self.frame_installed, height=100, state="disabled")
        self.textbox_log.pack(fill="x", padx=10, pady=(0, 10))

    def log(self, message):
        def _log():
            self.textbox_log.configure(state="normal")
            self.textbox_log.insert("end", message + "\n")
            self.textbox_log.see("end")
            self.textbox_log.configure(state="disabled")
        self.after(0, _log)

    def setup_bindings(self):
        self.bind("<Control-c>", self.copy_text)
        self.bind("<Control-C>", self.copy_text)
        self.bind("<Control-v>", self.paste_text)
        self.bind("<Control-V>", self.paste_text)
        self.bind("<Control-x>", self.cut_text)
        self.bind("<Control-X>", self.cut_text)
        self.bind("<Control-a>", self.select_all)
        self.bind("<Control-A>", self.select_all)
        
        # Безопасный бинд для русской раскладки
        for key, handler in [
            ("<Control-с>", self.copy_text), ("<Control-С>", self.copy_text),
            ("<Control-м>", self.paste_text), ("<Control-М>", self.paste_text),
            ("<Control-ч>", self.cut_text), ("<Control-Ч>", self.cut_text),
            ("<Control-ф>", self.select_all), ("<Control-Ф>", self.select_all)
        ]:
            try:
                self.bind(key, handler)
            except Exception:
                pass

    def copy_text(self, event=None):
        try:
            widget = self.focus_get()
            if hasattr(widget, 'selection_get'):
                text = widget.selection_get()
                self.clipboard_clear()
                self.clipboard_append(text)
        except Exception: pass
        return "break"

    def paste_text(self, event=None):
        try:
            widget = self.focus_get()
            if hasattr(widget, 'insert'):
                clipboard = self.clipboard_get()
                try: widget.delete("sel.first", "sel.last")
                except Exception: pass
                widget.insert("insert", clipboard)
        except Exception: pass
        return "break"

    def cut_text(self, event=None):
        try:
            widget = self.focus_get()
            if hasattr(widget, 'selection_get') and hasattr(widget, 'delete'):
                text = widget.selection_get()
                self.clipboard_clear()
                self.clipboard_append(text)
                widget.delete("sel.first", "sel.last")
        except Exception: pass
        return "break"

    def select_all(self, event=None):
        try:
            widget = self.focus_get()
            if hasattr(widget, 'select_range'):
                widget.select_range(0, 'end')
                widget.icursor('end')
            elif hasattr(widget, 'tag_add'):
                widget.tag_add("sel", "1.0", "end")
        except Exception: pass
        return "break"

    def load_settings(self):
        config = load_config()
        self.entry_api.insert(0, config.get("api_key", ""))
        self.entry_path.insert(0, config.get("addons_path", "C:\\Program Files (x86)\\World of Warcraft\\_retail_\\Interface\\AddOns"))
        self.option_version.set(config.get("game_version", "Retail (The War Within)"))

    def save_settings(self):
        config = load_config()
        config["api_key"] = self.entry_api.get().strip()
        config["addons_path"] = self.entry_path.get().strip()
        config["game_version"] = self.option_version.get()
        save_config(config)
        self.lbl_status.configure(text="Сохранено!", text_color="green")
        self.after(3000, lambda: self.lbl_status.configure(text=""))

    def do_browse_path(self):
        folder = ctk.filedialog.askdirectory(title="Выберите папку AddOns")
        if folder:
            # Заменяем слеши на обратные для красоты в Windows, хотя питон ест любые
            folder = folder.replace("/", "\\")
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, folder)

    def do_load_api_file(self):
        filepath = ctk.filedialog.askopenfilename(title="Выберите файл с API ключом", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    key = f.read().strip()
                self.entry_api.delete(0, "end")
                self.entry_api.insert(0, key)
                self.log(f"API ключ успешно загружен из {filepath}")
            except Exception as e:
                self.log(f"Ошибка при чтении файла ключа: {e}")

    def do_search(self):
        query = self.entry_search.get().strip()
        api_key = self.entry_api.get().strip()
        if not api_key:
            self.lbl_status.configure(text="API ключ не задан!", text_color="red")
            self.tabview.set("Настройки")
            return

        self.btn_search.configure(state="disabled", text="Ищем...")
        
        # Clear previous results
        for widget in self.scroll_search.winfo_children():
            widget.destroy()

        def fetch():
            results, error = search_addons(query, api_key)
            self.after(0, lambda: self.display_results(results, error))

        threading.Thread(target=fetch, daemon=True).start()

    def display_results(self, results, error):
        self.btn_search.configure(state="normal", text="Найти")
        if error:
            for widget in self.scroll_search.winfo_children(): widget.destroy()
            lbl = ctk.CTkLabel(self.scroll_search, text=error, text_color="red", wraplength=700)
            lbl.pack(pady=10)
            return
        self.display_search_results(results)

    def display_search_results(self, results):
        self.last_search_results = results
        installed_ids = load_config().get("addon_ids", [])
        
        for widget in self.scroll_search.winfo_children():
            widget.destroy()

        for res in results:
            card = ctk.CTkFrame(self.scroll_search, corner_radius=20, fg_color="#25252B")
            card.pack(fill="x", pady=8, padx=10)
            
            lbl_icon = ctk.CTkLabel(card, text="", width=50, height=50, corner_radius=15, fg_color="gray50")
            lbl_icon.pack(side="left", padx=15, pady=15)
            
            if res.get('logoUrl'):
                def set_img(img, l=lbl_icon): l.configure(image=img, fg_color="transparent")
                self.image_loader.get_image(res['logoUrl'], size=(50, 50), callback=lambda img, l=lbl_icon: self.after(0, lambda: set_img(img, l)))
            
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=(0, 15), pady=10)

            lbl_name = ctk.CTkLabel(info_frame, text=res['name'], font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
            lbl_name.pack(fill="x")
            
            lbl_author = ctk.CTkLabel(info_frame, text=f"Автор: {res['author']}", font=ctk.CTkFont(size=12), text_color="gray", anchor="w")
            lbl_author.pack(fill="x")

            lbl_summary = ctk.CTkLabel(info_frame, text=res.get('summary', ''), font=ctk.CTkFont(size=12), wraplength=450, justify="left", anchor="w")
            lbl_summary.pack(fill="x", pady=(5, 0))

            if res['id'] in installed_ids:
                btn_action = ctk.CTkButton(card, text="Удалить", width=110, height=35, corner_radius=15, fg_color="#D32F2F", hover_color="#B71C1C",
                                            command=lambda r=res: self.do_uninstall(r['id'], from_search=True))
            else:
                btn_action = ctk.CTkButton(card, text="Установить", width=110, height=35, corner_radius=15, fg_color="#F45821", hover_color="#FF7243",
                                            command=lambda r=res: self.do_install(r['id']))
            btn_action.pack(side="right", padx=15, pady=10)

    def do_install(self, addon_id):
        self.show_installed()
        self.log(f"\n--- Запуск установки ID: {addon_id} ---")
        
        def process():
            self.after(0, lambda: self.btn_update.configure(state="disabled"))
            install_addon(addon_id, log_callback=self.log)
            self.after(0, lambda: self.btn_update.configure(state="normal"))
            self.after(0, self.refresh_installed_list)
            if hasattr(self, 'last_search_results'):
                self.after(0, lambda: self.display_search_results(self.last_search_results))
            
        threading.Thread(target=process, daemon=True).start()



    def do_update_all(self):
        self.log("\n--- Запуск массового обновления ---")
        def process():
            self.after(0, lambda: self.btn_update.configure(state="disabled"))
            if hasattr(self, 'btn_reinstall_all'): self.after(0, lambda: self.btn_reinstall_all.configure(state="disabled"))
            update_all(log_callback=self.log)
            self.after(0, lambda: self.btn_update.configure(state="normal"))
            if hasattr(self, 'btn_reinstall_all'): self.after(0, lambda: self.btn_reinstall_all.configure(state="normal"))
            self.after(0, self.refresh_installed_list)
            
        threading.Thread(target=process, daemon=True).start()

    def do_reinstall_all(self):
        self.log("\n--- Запуск полной переустановки всех аддонов ---")
        def process():
            self.after(0, lambda: self.btn_update.configure(state="disabled"))
            if hasattr(self, 'btn_reinstall_all'): self.after(0, lambda: self.btn_reinstall_all.configure(state="disabled"))
            
            config = load_config()
            addon_ids = config.get("addon_ids", [])
            
            for aid in addon_ids:
                uninstall_addon(aid, log_callback=self.log)
                install_addon(aid, log_callback=self.log)
                import time
                time.sleep(1)
                
            self.after(0, lambda: self.btn_update.configure(state="normal"))
            if hasattr(self, 'btn_reinstall_all'): self.after(0, lambda: self.btn_reinstall_all.configure(state="normal"))
            self.after(0, self.refresh_installed_list)
            
        threading.Thread(target=process, daemon=True).start()

    def do_import(self):
        source_path = ctk.filedialog.askdirectory(title="Выберите папку ОТКУДА клонировать аддоны")
        if not source_path:
            return
            
        self.btn_export.configure(state="disabled")
        self.log(f"\n--- Запуск импорта из: {source_path} ---")
        
        def process():
            self.after(0, lambda: self.btn_update.configure(state="disabled"))
            import_addons(source_path, log_callback=self.log)
            self.after(0, lambda: self.btn_update.configure(state="normal"))
            self.after(0, lambda: self.btn_export.configure(state="normal"))
            self.after(0, self.refresh_installed_list)
            
        threading.Thread(target=process, daemon=True).start()

    def do_export_list(self):
        filepath = ctk.filedialog.asksaveasfilename(
            title="Сохранить список аддонов",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="my_addons.json"
        )
        if filepath:
            export_addon_list(filepath, log_callback=self.log)

    def do_import_list(self):
        filepath = ctk.filedialog.askopenfilename(
            title="Загрузить список аддонов",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filepath:
            return
            
        self.log(f"\n--- Импорт списка из {filepath} ---")
        self.btn_import_list.configure(state="disabled")
        self.btn_update.configure(state="disabled")
        
        def process():
            import_addon_list(filepath, log_callback=self.log)
            self.after(0, lambda: self.btn_import_list.configure(state="normal"))
            self.after(0, lambda: self.btn_update.configure(state="normal"))
            self.after(0, self.refresh_installed_list)
            
        threading.Thread(target=process, daemon=True).start()

    def refresh_installed_list(self):
        for widget in self.scroll_installed.winfo_children():
            widget.destroy()

        filter_text = ""
        if hasattr(self, 'var_filter'):
            filter_text = self.var_filter.get().strip().lower()

        addons = get_installed_addons()
        unmanaged = get_unmanaged_addons()
        
        if filter_text:
            addons = [a for a in addons if filter_text in a['name'].lower() or filter_text in str(a['id'])]
            unmanaged = [a for a in unmanaged if filter_text in a['name'].lower()]

        all_items = addons + unmanaged

        if not all_items:
            lbl = ctk.CTkLabel(self.scroll_installed, text="Нет установленных аддонов.", text_color="gray")
            lbl.pack(pady=20)
            return

        for a in all_items:
            card = ctk.CTkFrame(self.scroll_installed, corner_radius=20, fg_color="#25252B")
            card.pack(fill="x", pady=8, padx=10)
            
            lbl_icon = ctk.CTkLabel(card, text="", width=40, height=40, corner_radius=12, fg_color="gray50")
            lbl_icon.pack(side="left", padx=15, pady=15)
            
            if a.get('logoUrl'):
                def set_img(img, l=lbl_icon): l.configure(image=img, fg_color="transparent")
                self.image_loader.get_image(a['logoUrl'], size=(40, 40), callback=lambda img, l=lbl_icon: self.after(0, lambda: set_img(img, l)))

            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=(0, 15), pady=10)

            lbl_name = ctk.CTkLabel(info_frame, text=a['name'], font=ctk.CTkFont(size=15, weight="bold"), anchor="w")
            lbl_name.pack(fill="x")
            
            lbl_id = ctk.CTkLabel(info_frame, text=f"ID: {a['id']}", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
            lbl_id.pack(fill="x")

            btn_del = ctk.CTkButton(card, text="Удалить", width=80, height=32, corner_radius=15, fg_color="#D32F2F", hover_color="#B71C1C",
                                    command=lambda aid=a["id"]: self.do_uninstall(aid))
            btn_del.pack(side="right", padx=10, pady=10)

            is_managed = not (isinstance(a["id"], str) and not str(a["id"]).isdigit())
            if is_managed:
                btn_reinstall = ctk.CTkButton(card, text="Переустановить", width=100, height=32, corner_radius=15, fg_color="#F57C00", hover_color="#E65100",
                                        command=lambda aid=a["id"]: self.do_reinstall(aid))
                btn_reinstall.pack(side="right", padx=10, pady=10)
            
    def do_uninstall(self, addon_id, from_search=False):
        self.log(f"\n--- Удаление аддона ID: {addon_id} ---")
        def process():
            if isinstance(addon_id, str) and not str(addon_id).isdigit():
                uninstall_unmanaged_addon(addon_id, log_callback=self.log)
            else:
                uninstall_addon(int(addon_id), log_callback=self.log)
            self.after(0, self.refresh_installed_list)
            if hasattr(self, 'last_search_results'):
                self.after(0, lambda: self.display_search_results(self.last_search_results))
        threading.Thread(target=process, daemon=True).start()

    def do_reinstall(self, addon_id):
        self.log(f"\n--- Переустановка аддона ID: {addon_id} ---")
        def process():
            if isinstance(addon_id, str) and not str(addon_id).isdigit():
                self.log(f"Невозможно переустановить локальный аддон {addon_id}. Удалите его вручную.")
            else:
                uninstall_addon(int(addon_id), log_callback=self.log)
                install_addon(int(addon_id), log_callback=self.log)
            self.after(0, self.refresh_installed_list)
        threading.Thread(target=process, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
