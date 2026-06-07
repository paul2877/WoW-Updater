import json
import os

with open("downloader.py", "r", encoding="utf-8") as f:
    dl_content = f.read()

# Add profile management functions to downloader.py
profiles_code = '''
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
    
    if log_callback: log_callback(f"\\n--- Переключение на профиль: {new_profile_name} ---")
    
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
'''

with open("downloader.py", "a", encoding="utf-8") as f:
    f.write("\n\n" + profiles_code)

with open("gui.py", "r", encoding="utf-8") as f:
    gui_content = f.read()

# Add profile UI to gui.py
profile_ui = '''
        self.btn_export_list = ctk.CTkButton(frame_top, text="Сохранить список", fg_color="#1976D2", hover_color="#1565C0", command=self.do_export_list)
        self.btn_export_list.pack(side="left", padx=(0, 10))
        
        # UI Профилей
        self.profile_var = ctk.StringVar()
        self.combo_profile = ctk.CTkComboBox(frame_top, variable=self.profile_var, values=["Default"], width=120, command=self.do_switch_profile)
        self.combo_profile.pack(side="left", padx=(10, 5))
        
        self.btn_new_profile = ctk.CTkButton(frame_top, text="+", width=30, fg_color="#388E3C", hover_color="#2E7D32", command=self.do_new_profile)
        self.btn_new_profile.pack(side="left", padx=(0, 10))
        
        self.update_profiles_ui()
'''
gui_content = gui_content.replace(
    '        self.btn_export_list = ctk.CTkButton(frame_top, text="Сохранить список", fg_color="#1976D2", hover_color="#1565C0", command=self.do_export_list)\n        self.btn_export_list.pack(side="left", padx=(0, 10))',
    profile_ui
)

profile_funcs = '''
    def update_profiles_ui(self):
        profiles, current = downloader.get_profiles()
        if hasattr(self, 'combo_profile'):
            self.combo_profile.configure(values=profiles)
            self.profile_var.set(current)

    def do_switch_profile(self, selected_profile):
        _, current = downloader.get_profiles()
        if selected_profile == current:
            return
            
        self.log(f"Переключение на профиль {selected_profile}...")
        self.combo_profile.configure(state="disabled")
        
        def process():
            downloader.switch_profile(selected_profile, log_callback=self.log, progress_callback_factory=self.get_progress_callback)
            self.after(0, lambda: self.combo_profile.configure(state="normal"))
            self.after(0, self.refresh_installed_list)
            self.after(0, self.update_profiles_ui)
            
        import threading
        threading.Thread(target=process, daemon=True).start()
        
    def do_new_profile(self):
        dialog = ctk.CTkInputDialog(text="Введите имя нового профиля:", title="Новый профиль")
        name = dialog.get_input()
        if name:
            profiles, _ = downloader.get_profiles()
            if name not in profiles:
                config = downloader.load_config()
                if "profiles" not in config:
                    config["profiles"] = {"Default": config.get("addon_ids", [])}
                config["profiles"][name] = []
                downloader.save_config(config)
                self.update_profiles_ui()
                self.profile_var.set(name)
                self.do_switch_profile(name)
'''

gui_content = gui_content + '\n' + profile_funcs

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(gui_content)
