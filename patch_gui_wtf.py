import re

with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add button to setup_settings_tab
btn_code = '''
        self.btn_backup = ctk.CTkButton(self.scroll_settings, text="Бэкап настроек (WTF)", height=40, font=ctk.CTkFont(size=14), fg_color="#1976D2", hover_color="#1565C0", command=self.do_backup_wtf)
        self.btn_backup.pack(pady=10, fill="x", padx=100)
'''

content = content.replace('        self.btn_save_settings.pack(pady=20)', '        self.btn_save_settings.pack(pady=20)' + btn_code)

func_code = '''
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
            
        self.log(f"\\n--- Резервное копирование WTF в {filepath} ---")
        self.btn_backup.configure(state="disabled")
        
        def process():
            downloader.backup_wtf(filepath, log_callback=self.log)
            self.after(0, lambda: self.btn_backup.configure(state="normal"))
            
        threading.Thread(target=process, daemon=True).start()
'''

content = content + '\n' + func_code

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
