code = """
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
"""
with open('downloader.py', 'a', encoding='utf-8') as f:
    f.write('\n\n' + code)
