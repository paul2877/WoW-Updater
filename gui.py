import customtkinter as ctk
import threading
import downloader
import wago_scraper
import wago_lua_generator
from downloader import get_profiles
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

        self.nav_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.nav_frame.grid(row=1, column=0, sticky="ew")

        self.btn_nav_installed = ctk.CTkButton(self.nav_frame, text="Установленные", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=self.show_installed)
        self.btn_nav_installed.pack(pady=10, padx=20, fill="x")

        self.btn_nav_search = ctk.CTkButton(self.nav_frame, text="Поиск аддонов", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=self.show_search)
        self.btn_nav_search.pack(pady=10, padx=20, fill="x")
        
        self.btn_nav_wago = ctk.CTkButton(self.nav_frame, text="WeakAuras (Wago)", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=self.show_wago)
        self.btn_nav_wago.pack(pady=10, padx=20, fill="x")

        self.btn_nav_settings = ctk.CTkButton(self.nav_frame, text="Настройки", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=self.show_settings)
        self.btn_nav_settings.pack(pady=10, padx=20, fill="x")

        self.lbl_copyright = ctk.CTkLabel(self.sidebar_frame, text="© angeldev", font=ctk.CTkFont(size=11), text_color="gray40")
        self.lbl_copyright.grid(row=5, column=0, pady=20, sticky="s")

        # Main Content Frames
        self.frame_installed = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_search = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_settings = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_wago = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        self.setup_settings_tab()
        self.setup_search_tab()
        self.setup_wago_tab()
        self.setup_installed_tab()
        self.setup_bindings()

        self.load_settings()
        self.show_installed()
        self.refresh_installed_list()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.tray_icon = None
        self.bg_timer_thread = threading.Thread(target=self.bg_updater_loop, daemon=True)
        self.bg_timer_thread.start()


    def select_nav_button(self, name):
        self.btn_nav_installed.configure(fg_color="#F45821" if name == "installed" else "transparent")
        self.btn_nav_search.configure(fg_color="#F45821" if name == "search" else "transparent")
        self.btn_nav_settings.configure(fg_color="#F45821" if name == "settings" else "transparent")
        self.btn_nav_wago.configure(fg_color="#F45821" if name == "wago" else "transparent")

    def show_installed(self):
        self.select_nav_button("installed")
        self.frame_search.grid_forget()
        self.frame_settings.grid_forget()
        self.frame_wago.grid_forget()
        self.frame_installed.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_search(self):
        self.select_nav_button("search")
        self.frame_installed.grid_forget()
        self.frame_settings.grid_forget()
        self.frame_wago.grid_forget()
        self.frame_search.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_settings(self):
        self.select_nav_button("settings")
        self.frame_installed.grid_forget()
        self.frame_search.grid_forget()
        self.frame_wago.grid_forget()
        self.frame_settings.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def show_wago(self):
        self.select_nav_button("wago")
        self.frame_installed.grid_forget()
        self.frame_search.grid_forget()
        self.frame_settings.grid_forget()
        self.frame_wago.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.switch_wago_mode("search")

    def switch_wago_mode(self, mode):
        self.btn_wago_mode_search.configure(fg_color="#F45821" if mode == "search" else "transparent")
        self.btn_wago_mode_installed.configure(fg_color="#F45821" if mode == "installed" else "transparent")
        
        if mode == "search":
            self.wago_installed_container.pack_forget()
            self.wago_search_container.pack(fill="both", expand=True)
        else:
            self.wago_search_container.pack_forget()
            self.wago_installed_container.pack(fill="both", expand=True)
            self.refresh_installed_wagos()

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

    def setup_wago_tab(self):
        tabs_frame = ctk.CTkFrame(self.frame_wago, fg_color="transparent")
        tabs_frame.pack(fill="x", padx=10, pady=(10, 0))
        
        self.btn_wago_mode_search = ctk.CTkButton(tabs_frame, text="Поиск аур", width=120, fg_color="#F45821", command=lambda: self.switch_wago_mode("search"))
        self.btn_wago_mode_search.pack(side="left", padx=5)
        
        self.btn_wago_mode_installed = ctk.CTkButton(tabs_frame, text="Мои ауры", width=120, fg_color="transparent", text_color="gray90", hover_color=("gray70", "gray30"), command=lambda: self.switch_wago_mode("installed"))
        self.btn_wago_mode_installed.pack(side="left", padx=5)

        self.wago_search_container = ctk.CTkFrame(self.frame_wago, fg_color="transparent")
        self.wago_search_container.pack(fill="both", expand=True)
        
        self.wago_installed_container = ctk.CTkFrame(self.frame_wago, fg_color="transparent")

        # Setup Search Sub-tab
        frame_top = ctk.CTkFrame(self.wago_search_container, fg_color="transparent")
        frame_top.pack(fill="x", padx=10, pady=10)

        self.entry_wago_search = ctk.CTkEntry(frame_top, placeholder_text="Поиск WeakAuras...", width=400)
        self.entry_wago_search.pack(side="left", padx=(0, 10))

        self.btn_wago_search = ctk.CTkButton(frame_top, text="Найти Wago", fg_color="#F45821", hover_color="#FF7243", command=self.do_wago_search)
        self.btn_wago_search.pack(side="left")

        self.wago_status = ctk.CTkLabel(frame_top, text="", text_color="green")
        self.wago_status.pack(side="left", padx=10)

        self.scroll_wago = ctk.CTkScrollableFrame(self.wago_search_container)
        self.scroll_wago.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Setup Installed Sub-tab
        self.scroll_wago_installed = ctk.CTkScrollableFrame(self.wago_installed_container)
        self.scroll_wago_installed.pack(fill="both", expand=True, padx=10, pady=10)

    def setup_installed_tab(self):
        frame_top = ctk.CTkFrame(self.frame_installed, fg_color="transparent")
        frame_top.pack(fill="x", padx=10, pady=(10, 0))

        self.btn_update = ctk.CTkButton(frame_top, text="Обновить всё", fg_color="#F45821", hover_color="#FF7243", command=self.do_update_all)
        self.btn_update.pack(side="left", padx=(0, 10))

        self.btn_reinstall_all = ctk.CTkButton(frame_top, text="Переустановить всё", fg_color="#C2185B", hover_color="#AD1457", command=self.do_reinstall_all)
        self.btn_reinstall_all.pack(side="left", padx=(0, 10))
        
        self.btn_export = ctk.CTkButton(frame_top, text="Клонировать сборку", fg_color="#F57C00", hover_color="#E65100", command=self.do_import)
        self.btn_export.pack(side="left", padx=(0, 10))

        self.btn_scan = ctk.CTkButton(frame_top, text="Найти локальные", fg_color="#1E88E5", hover_color="#1565C0", command=self.do_scan_local)
        self.btn_scan.pack(side="left", padx=(0, 10))


        self.btn_export_list = ctk.CTkButton(frame_top, text="Сохранить список", fg_color="#1976D2", hover_color="#1565C0", command=self.do_export_list)
        self.btn_export_list.pack(side="left", padx=(0, 10))
        
        # UI Профилей
        self.profile_var = ctk.StringVar()
        self.combo_profile = ctk.CTkComboBox(frame_top, variable=self.profile_var, values=["Default"], width=120, command=self.do_switch_profile)
        self.combo_profile.pack(side="left", padx=(10, 5))
        
        self.btn_new_profile = ctk.CTkButton(frame_top, text="+", width=30, fg_color="#388E3C", hover_color="#2E7D32", command=self.do_new_profile)
        self.btn_new_profile.pack(side="left", padx=(0, 10))
        
        self.update_profiles_ui()

        
        self.btn_import_list = ctk.CTkButton(frame_top, text="Загрузить из списка", fg_color="#388E3C", hover_color="#2E7D32", command=self.do_import_list)
        self.btn_import_list.pack(side="left")

        frame_filter = ctk.CTkFrame(self.frame_installed, fg_color="transparent")
        frame_filter.pack(fill="x", padx=10, pady=(10, 0))

        self.var_filter = ctk.StringVar()
        self.var_filter.trace_add("write", lambda *args: self.render_installed_list())
        
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
            
            btn_versions = ctk.CTkButton(card, text="Версии", width=80, height=35, corner_radius=15, fg_color="#1E88E5", hover_color="#1565C0",
                                        command=lambda r=res: self.show_versions_window(r['id'], r['name']))
            btn_versions.pack(side="right", padx=(0, 10), pady=10)

    def do_wago_search(self):
        query = self.entry_wago_search.get().strip()
        if not query:
            return

        self.btn_wago_search.configure(state="disabled", text="Ищем...")
        self.wago_status.configure(text="", text_color="green")
        
        for widget in self.scroll_wago.winfo_children():
            widget.destroy()

        def fetch():
            results = wago_scraper.search_wago(query)
            self.after(0, lambda: self.display_wago_results(results))

        threading.Thread(target=fetch, daemon=True).start()

    def display_wago_results(self, results):
        self.btn_wago_search.configure(state="normal", text="Найти Wago")
        if not results:
            lbl = ctk.CTkLabel(self.scroll_wago, text="Ничего не найдено.", text_color="gray")
            lbl.pack(pady=10)
            return

        for res in results:
            card = ctk.CTkFrame(self.scroll_wago, corner_radius=20, fg_color="#25252B")
            card.pack(fill="x", pady=8, padx=10)
            
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=10)

            lbl_name = ctk.CTkLabel(info_frame, text=res['name'], font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
            lbl_name.pack(fill="x")
            
            lbl_author = ctk.CTkLabel(info_frame, text=f"Автор: {res['author']} | Установок: {res['installs']}", font=ctk.CTkFont(size=12), text_color="gray", anchor="w")
            lbl_author.pack(fill="x")

            btn_details = ctk.CTkButton(card, text="Подробнее", width=110, height=35, corner_radius=15, fg_color="#455A64", hover_color="#546E7A",
                                        command=lambda r=res: self.show_wago_details(r))
            btn_details.pack(side="right", padx=15, pady=10)

            btn_install = ctk.CTkButton(card, text="Установить", width=110, height=35, corner_radius=15, fg_color="#00ACC1", hover_color="#00838F",
                                        command=lambda r=res: self.do_wago_install(r))
            btn_install.pack(side="right", padx=5, pady=10)

    def show_wago_details(self, res):
        modal = ctk.CTkToplevel(self)
        modal.title(f"Детали ауры: {res['name']}")
        modal.geometry("600x500")
        modal.transient(self)
        modal.grab_set()

        scroll = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        lbl_name = ctk.CTkLabel(scroll, text=res['name'], font=ctk.CTkFont(size=20, weight="bold"))
        lbl_name.pack(pady=(0, 10), anchor="w")

        lbl_meta = ctk.CTkLabel(scroll, text=f"Автор: {res['author']} | ID: {res['slug']}", text_color="gray")
        lbl_meta.pack(pady=(0, 20), anchor="w")

        lbl_desc = ctk.CTkLabel(scroll, text=res['description'], wraplength=540, justify="left")
        lbl_desc.pack(pady=10, anchor="w")

        config = downloader.load_config()
        addons_path = config.get("addons_path", "")
        wa_installed = addons_path and os.path.exists(os.path.join(addons_path, "WeakAuras"))

        if not wa_installed:
            lbl_warning = ctk.CTkLabel(modal, text="⚠️ Для установки аур сначала скачайте базовый аддон WeakAuras!", text_color="red", font=ctk.CTkFont(weight="bold"))
            lbl_warning.pack(pady=(10, 0))

        btn_install = ctk.CTkButton(modal, text="Скачать и Установить в игру", fg_color="#F45821", hover_color="#FF7243", height=40,
                                    state="normal" if wa_installed else "disabled",
                                    command=lambda: [modal.destroy(), self.do_wago_install(res)])
        btn_install.pack(pady=20, padx=20, fill="x")

    def do_wago_install(self, res):
        self.wago_status.configure(text=f"Скачиваем {res['name']}...", text_color="#00ACC1")
        
        def fetch():
            wago_string = wago_scraper.extract_wago_string(res['slug'])
            def on_done():
                if wago_string:
                    config = downloader.load_config()
                    addons_path = config.get("addons_path", "")
                    if addons_path and os.path.exists(addons_path):
                        if not os.path.exists(os.path.join(addons_path, "WeakAuras")):
                            self.wago_status.configure(text="Ошибка: базовый аддон WeakAuras не установлен!", text_color="red")
                        else:
                            wago_lua_generator.add_wago_to_companion(addons_path, res['slug'], res['name'], wago_string, res['author'])
                            self.wago_status.configure(text="Готово! Зайдите в игру и откройте /wa", text_color="green")
                            self.refresh_installed_wagos()
                    else:
                        self.wago_status.configure(text="Ошибка: неверный путь к аддонам в настройках.", text_color="red")
                else:
                    self.wago_status.configure(text="Открыта страница ауры в браузере", text_color="#FFB300")
            self.after(0, on_done)
            
        threading.Thread(target=fetch, daemon=True).start()

    def refresh_installed_wagos(self):
        config = downloader.load_config()
        addons_path = config.get("addons_path", "")
        wagos = wago_lua_generator.get_installed_wagos(addons_path)
        
        for widget in self.scroll_wago_installed.winfo_children():
            widget.destroy()
            
        if not wagos:
            lbl = ctk.CTkLabel(self.scroll_wago_installed, text="У вас пока нет установленных аур от Wago.io", text_color="gray")
            lbl.pack(pady=20)
            return
            
        for w in wagos:
            card = ctk.CTkFrame(self.scroll_wago_installed, corner_radius=20, fg_color="#25252B")
            card.pack(fill="x", pady=8, padx=10)
            
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=15, pady=10)

            lbl_name = ctk.CTkLabel(info_frame, text=w['name'], font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
            lbl_name.pack(fill="x")
            
            lbl_author = ctk.CTkLabel(info_frame, text=f"Автор: {w['author']} | ID: {w['slug']}", font=ctk.CTkFont(size=12), text_color="gray", anchor="w")
            lbl_author.pack(fill="x")

            btn_del = ctk.CTkButton(card, text="Удалить", width=110, height=35, corner_radius=15, fg_color="#D32F2F", hover_color="#B71C1C",
                                        command=lambda slug=w['slug']: self.do_wago_delete(slug))
            btn_del.pack(side="right", padx=15, pady=10)
            
    def do_wago_delete(self, slug):
        config = downloader.load_config()
        addons_path = config.get("addons_path", "")
        wago_lua_generator.remove_wago(addons_path, slug)
        self.refresh_installed_wagos()
    def get_progress_callback(self, addon_id):
        aid_str = str(addon_id)
        if hasattr(self, 'progress_bars') and aid_str in self.progress_bars:
            pb = self.progress_bars[aid_str]
            self.after(0, lambda: pb.pack(fill="x", pady=(5, 0)))
            def callback(downloaded, total):
                if total > 0:
                    self.after(0, lambda: pb.set(downloaded / total))
            return callback
        return None

    def do_install(self, addon_id):
        self.show_installed()
        self.log(f"\n--- Запуск установки ID: {addon_id} ---")
        
        def process():
            self.after(0, lambda: self.btn_update.configure(state="disabled"))
            cb = self.get_progress_callback(addon_id)
            downloader.install_addon(addon_id, log_callback=self.log, progress_callback=cb)
            self.after(0, lambda: self.btn_update.configure(state="normal"))
            self.after(0, self.refresh_installed_list)
            if hasattr(self, 'last_search_results'):
                self.after(0, lambda: self.display_search_results(self.last_search_results))
        threading.Thread(target=process, daemon=True).start()

    def do_update_all(self):
        self.log("\\n--- Запуск массового обновления ---")
        def process():
            self.after(0, lambda: self.btn_update.configure(state="disabled"))
            if hasattr(self, 'btn_reinstall_all'): self.after(0, lambda: self.btn_reinstall_all.configure(state="disabled"))
            downloader.update_all(log_callback=self.log, progress_callback_factory=self.get_progress_callback)
            self.after(0, lambda: self.btn_update.configure(state="normal"))
            if hasattr(self, 'btn_reinstall_all'): self.after(0, lambda: self.btn_reinstall_all.configure(state="normal"))
            self.after(0, self.refresh_installed_list)
        threading.Thread(target=process, daemon=True).start()

    def do_reinstall_all(self):
        self.log("\\n--- Запуск полной переустановки всех аддонов ---")
        def process():
            self.after(0, lambda: self.btn_update.configure(state="disabled"))
            if hasattr(self, 'btn_reinstall_all'): self.after(0, lambda: self.btn_reinstall_all.configure(state="disabled"))
            
            config = downloader.load_config()
            addon_ids = config.get("addon_ids", [])
            
            for aid in addon_ids:
                cb = self.get_progress_callback(aid)
                downloader.install_addon(aid, log_callback=self.log, progress_callback=cb, force_reinstall=True)
                import time
                time.sleep(1)
                
            self.after(0, lambda: self.btn_update.configure(state="normal"))
            if hasattr(self, 'btn_reinstall_all'): self.after(0, lambda: self.btn_reinstall_all.configure(state="normal"))
            self.after(0, self.refresh_installed_list)
            
        threading.Thread(target=process, daemon=True).start()

    def do_scan_local(self):
        self.log("\n--- Запуск поиска локальных аддонов ---")
        self.btn_scan.configure(state="disabled")
        def process():
            total_found, recognized = downloader.scan_local_addons(log_callback=self.log)
            self.after(0, lambda: self.btn_scan.configure(state="normal"))
            if total_found > 0:
                self.log(f"[*] Сканирование завершено. Распознано {recognized} из {total_found} аддонов.")
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
        # Load data once, then render
        self.cached_installed = downloader.get_installed_addons()
        self.cached_unmanaged = downloader.get_unmanaged_addons()
        self.render_installed_list()

    def render_installed_list(self):
        for widget in self.scroll_installed.winfo_children():
            widget.destroy()

        filter_text = ""
        if hasattr(self, 'var_filter'):
            filter_text = self.var_filter.get().strip().lower()

        addons = getattr(self, 'cached_installed', [])
        unmanaged = getattr(self, 'cached_unmanaged', [])
        
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
            
            pb = ctk.CTkProgressBar(info_frame, height=5, fg_color="#333", progress_color="#F45821")
            pb.set(0)
            pb.pack(fill="x", pady=(5, 0))
            pb.pack_forget() # Скрываем по умолчанию
            if not hasattr(self, 'progress_bars'): self.progress_bars = {}
            self.progress_bars[str(a['id'])] = pb

            btn_del = ctk.CTkButton(card, text="Удалить", width=80, height=32, corner_radius=15, fg_color="#D32F2F", hover_color="#B71C1C",
                                    command=lambda aid=a["id"]: self.do_uninstall(aid))
            btn_del.pack(side="right", padx=10, pady=10)

            is_managed = not (isinstance(a["id"], str) and not str(a["id"]).isdigit())
            if is_managed:
                btn_reinstall = ctk.CTkButton(card, text="Переустановить", width=110, height=32, corner_radius=15, fg_color="#F57C00", hover_color="#E65100",
                                        command=lambda aid=a["id"]: self.do_reinstall(aid))
                btn_reinstall.pack(side="right", padx=10, pady=10)
                
                btn_versions = ctk.CTkButton(card, text="Версии", width=80, height=32, corner_radius=15, fg_color="#1E88E5", hover_color="#1565C0",
                                        command=lambda aid=a["id"], n=a["name"]: self.show_versions_window(aid, n))
                btn_versions.pack(side="right", padx=10, pady=10)
            
    def do_uninstall(self, aid):
        from tkinter import messagebox
        if messagebox.askyesno("Удаление", "Вы уверены, что хотите удалить этот аддон?"):
            if isinstance(aid, str) and not str(aid).isdigit():
                downloader.uninstall_unmanaged_addon(aid, log_callback=self.log)
            else:
                downloader.uninstall_addon(aid, log_callback=self.log)
            self.refresh_installed_list()

    def do_reinstall(self, aid):
        from tkinter import messagebox
        if messagebox.askyesno("Переустановка", "Будут удалены старые папки аддона и он будет скачан заново. Продолжить?"):
            def process():
                self.log(f"\\n--- Принудительная переустановка аддона (ID: {aid}) ---")
                cb = self.get_progress_callback(aid)
                downloader.install_addon(aid, log_callback=self.log, progress_callback=cb, force_reinstall=True)
                self.log("--- Переустановка завершена ---")
                self.after(0, self.refresh_installed_list)
            threading.Thread(target=process, daemon=True).start()

    def do_backup_wtf(self):
        import datetime
        date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = ctk.filedialog.asksaveasfilename(
            title="Сохранить бэкап WTF",
            defaultextension=".zip",
            filetypes=[("ZIP Archive", "*.zip")],
            initialfile=f"WTF_Backup_{date_str}.zip"
        )
        if not filepath:
            return
            
        self.log(f"\n--- Резервное копирование WTF в {filepath} ---")
        self.btn_backup.configure(state="disabled")
        
        def process():
            downloader.backup_wtf(filepath, log_callback=self.log)
            self.after(0, lambda: self.btn_backup.configure(state="normal"))
            
        threading.Thread(target=process, daemon=True).start()


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


    def bg_updater_loop(self):
        import time
        while True:
            time.sleep(3600) # Каждый час
            if self.state() == "withdrawn": # Только если свернут в трей
                self.log("Фоновое обновление по таймеру...")
                downloader.update_all(log_callback=self.log, progress_callback_factory=self.get_progress_callback)

    def on_closing(self):
        import pystray
        from PIL import Image, ImageDraw
        import io
        import base64
        
        self.withdraw() # Прячем окно
        
    def show_versions_window(self, addon_id, mod_name):
        win = ctk.CTkToplevel(self)
        win.title(f"Версии: {mod_name}")
        win.geometry("600x500")
        win.transient(self)
        win.grab_set()

        lbl_title = ctk.CTkLabel(win, text=f"Доступные версии для {mod_name}", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_title.pack(pady=(10, 5))

        lbl_status = ctk.CTkLabel(win, text="Загрузка...", text_color="gray")
        lbl_status.pack(pady=5)

        scroll = ctk.CTkScrollableFrame(win)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        def fetch_versions():
            try:
                config = downloader.load_config()
                api_key = config.get("api_key", "")
                if not api_key:
                    self.after(0, lambda: lbl_status.configure(text="Ошибка: нет API ключа", text_color="red"))
                    return
                
                files = downloader.get_addon_files(addon_id, api_key, log_callback=None)
                if not files:
                    self.after(0, lambda: lbl_status.configure(text="Версии не найдены", text_color="red"))
                    return
                
                self.after(0, lambda: populate_versions(files))
            except Exception as e:
                self.after(0, lambda: lbl_status.configure(text=f"Ошибка: {e}", text_color="red"))

        def populate_versions(files):
            lbl_status.destroy()
            for f in files:
                card = ctk.CTkFrame(scroll, fg_color="#25252B", corner_radius=10)
                card.pack(fill="x", pady=5)
                
                info_frame = ctk.CTkFrame(card, fg_color="transparent")
                info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
                
                lbl_name = ctk.CTkLabel(info_frame, text=f['fileName'], font=ctk.CTkFont(weight="bold"), anchor="w")
                lbl_name.pack(fill="x")
                
                rtype = "Release" if f.get("releaseType") == 1 else "Beta" if f.get("releaseType") == 2 else "Alpha"
                gvs = [gv.get("gameVersionName") for gv in f.get("sortableGameVersions", [])]
                gv_text = ", ".join(gvs[:3]) + ("..." if len(gvs) > 3 else "")
                
                lbl_desc = ctk.CTkLabel(info_frame, text=f"Тип: {rtype} | Патчи: {gv_text}", text_color="gray", anchor="w")
                lbl_desc.pack(fill="x")
                
                def on_install(fid=f['id']):
                    win.destroy()
                    self.do_install_specific(addon_id, mod_name, fid)
                    
                btn = ctk.CTkButton(card, text="Установить", width=100, command=on_install)
                btn.pack(side="right", padx=10, pady=10)

        threading.Thread(target=fetch_versions, daemon=True).start()

    def do_install_specific(self, addon_id, mod_name, file_id):
        self.log(f"\n--- Установка конкретной версии {mod_name} (Файл: {file_id}) ---")
        def process():
            success = downloader.install_addon(
                addon_id,
                log_callback=self.log,
                progress_callback=self.get_progress_callback(addon_id),
                force_reinstall=True,
                target_file_id=file_id
            )
            if success:
                self.after(0, self.refresh_installed_list)
        threading.Thread(target=process, daemon=True).start()

    def setup_tray(self):
        import pystray
        from PIL import Image
        import io
        import base64
        try:
            icon_data = base64.b64decode(get_icon_base64())
            image = Image.open(io.BytesIO(icon_data))
        except:
            image = Image.new('RGB', (64, 64), color=(244, 88, 33))
            
        menu = pystray.Menu(
            pystray.MenuItem("Открыть WoW Updater", self.on_tray_show),
            pystray.MenuItem("Обновить все", self.on_tray_update),
            pystray.MenuItem("Выход", self.on_tray_quit)
        )
        
        self.tray_icon = pystray.Icon("WoW Updater", image, "WoW Updater", menu)
        
        def run_tray():
            self.tray_icon.run()
            
        threading.Thread(target=run_tray, daemon=True).start()

    def on_tray_show(self, icon, item):
        self.tray_icon.stop()
        self.after(0, self.deiconify)
        
    def on_tray_update(self, icon, item):
        self.do_update_all()
        
    def on_tray_quit(self, icon, item):
        self.tray_icon.stop()
        self.after(0, self.destroy)

if __name__ == "__main__":
    app = App()
    app.mainloop()
