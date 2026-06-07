code = """
def scan_local_addons(log_callback=None):
    config = load_config()
    api_key = config.get("api_key")
    if not api_key:
        if log_callback: log_callback("[-] Ошибка: Отсутствует API-ключ.")
        return 0, 0
    
    addons_path = get_wow_addons_path()
    if not os.path.exists(addons_path):
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
"""
with open('downloader.py', 'a', encoding='utf-8') as f:
    f.write('\n\n' + code)
