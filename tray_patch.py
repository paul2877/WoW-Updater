import re

with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add to init
init_code = '''
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.tray_icon = None
        self.bg_timer_thread = threading.Thread(target=self.bg_updater_loop, daemon=True)
        self.bg_timer_thread.start()
'''

content = content.replace('        self.refresh_installed_list()', '        self.refresh_installed_list()' + init_code)


tray_funcs = '''
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
        
        # Создаем иконку
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
'''

# Find the end of App class
content = content.replace('if __name__ == "__main__":', tray_funcs + '\nif __name__ == "__main__":')

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
