import re

with open('gui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace tab variables
content = content.replace('self.tab_settings', 'self.frame_settings')
content = content.replace('self.tab_installed', 'self.frame_installed')
content = content.replace('self.tab_search', 'self.frame_search')
content = content.replace('self.tabview.set("Мои аддоны")', 'self.show_installed()')

# Replace init block
init_block_old = """    def __init__(self):
        super().__init__()

        self.title("WoW TWW Addon Updater")
        self.geometry("850x650")
        self.image_loader = ImageLoader()

        # Tabview
        self.tabview = ctk.CTkTabview(self, width=750, height=550)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)

        self.frame_installed = self.tabview.add("Мои аддоны")
        self.frame_search = self.tabview.add("Поиск")
        self.frame_settings = self.tabview.add("Настройки")

        self.setup_settings_tab()
        self.setup_search_tab()
        self.setup_installed_tab()
        self.setup_bindings()

        self.load_settings()
        self.refresh_installed_list()"""

init_block_new = """    def __init__(self):
        super().__init__()

        self.title("WoW Updater (CurseForge Style)")
        self.geometry("950x650")
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
        self.frame_settings.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)"""

content = content.replace(init_block_old, init_block_new)

# Fix button colors
content = content.replace('fg_color="#2E7D32", hover_color="#1B5E20"', 'fg_color="#F45821", hover_color="#FF7243"')
content = content.replace('self.btn_search = ctk.CTkButton(frame_top, text="Найти", command=self.do_search)', 'self.btn_search = ctk.CTkButton(frame_top, text="Найти", fg_color="#F45821", hover_color="#FF7243", command=self.do_search)')
content = content.replace('self.btn_update = ctk.CTkButton(frame_top, text="Обновить всё", command=self.do_update_all)', 'self.btn_update = ctk.CTkButton(frame_top, text="Обновить всё", fg_color="#F45821", hover_color="#FF7243", command=self.do_update_all)')

# Card colors
content = content.replace('fg_color=("gray85", "#2A2D32")', 'fg_color="#25252B"')

with open('gui.py', 'w', encoding='utf-8') as f:
    f.write(content)
