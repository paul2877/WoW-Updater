import customtkinter as ctk
import threading
import downloader
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
        config = downloader.load_config()
        self.entry_api.insert(0, config.get("api_key", ""))
        self.entry_path.insert(0, config.get("addons_path", "C:\\Program Files (x86)\\World of Warcraft\\_retail_\\Interface\\AddOns"))
        self.option_version.set(config.get("game_version", "Retail (The War Within)"))

    def save_settings(self):
        config = downloader.load_config()
        config["api_key"] = self.entry_api.get().strip()
        config["addons_path"] = self.entry_path.get().strip()
        config["game_version"] = self.option_version.get()
        downloader.save_config(config)
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
            results, error = downloader.search_addons(query, api_key)
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
        installed_ids = downloader.load_config().get("addon_ids", [])
        
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
            downloader.install_addon(addon_id, log_callback=self.log)
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
            downloader.update_all(log_callback=self.log)
            self.after(0, lambda: self.btn_update.configure(state="normal"))
            if hasattr(self, 'btn_reinstall_all'): self.after(0, lambda: self.btn_reinstall_all.configure(state="normal"))
            self.after(0, self.refresh_installed_list)
            
        threading.Thread(target=process, daemon=True).start()

    def do_reinstall_all(self):
        self.log("\n--- Запуск полной переустановки всех аддонов ---")
        def process():
            self.after(0, lambda: self.btn_update.configure(state="disabled"))
            if hasattr(self, 'btn_reinstall_all'): self.after(0, lambda: self.btn_reinstall_all.configure(state="disabled"))
            
            config = downloader.load_config()
            addon_ids = config.get("addon_ids", [])
            
            for aid in addon_ids:
                downloader.uninstall_addon(aid, log_callback=self.log)
                downloader.install_addon(aid, log_callback=self.log)
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
            downloader.import_addons(source_path, log_callback=self.log)
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
            downloader.export_addon_list(filepath, log_callback=self.log)

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
            downloader.import_addon_list(filepath, log_callback=self.log)
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

        addons = downloader.get_installed_addons()
        unmanaged = downloader.get_unmanaged_addons()
        
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
                downloader.uninstall_unmanaged_addon(addon_id, log_callback=self.log)
            else:
                downloader.uninstall_addon(int(addon_id), log_callback=self.log)
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
                downloader.uninstall_addon(int(addon_id), log_callback=self.log)
                downloader.install_addon(int(addon_id), log_callback=self.log)
            self.after(0, self.refresh_installed_list)
        threading.Thread(target=process, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
