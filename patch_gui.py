import re

with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add get_progress_callback
progress_cb_func = '''
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
'''
content = content.replace('    def do_install(self, addon_id):', progress_cb_func + '\n    def do_install(self, addon_id):')

# Update do_install
content = content.replace(
    'downloader.install_addon(addon_id, log_callback=self.log)',
    'cb = self.get_progress_callback(addon_id)\n            downloader.install_addon(addon_id, log_callback=self.log, progress_callback=cb)'
)

# Update do_update_all
content = content.replace(
    'downloader.update_all(log_callback=self.log)',
    'downloader.update_all(log_callback=self.log, progress_callback_factory=self.get_progress_callback)'
)

# Update do_reinstall_all
content = content.replace(
    'downloader.install_addon(aid, log_callback=self.log)',
    'cb = self.get_progress_callback(aid)\n                downloader.install_addon(aid, log_callback=self.log, progress_callback=cb)'
)

# Update do_reinstall
content = content.replace(
    'downloader.install_addon(int(addon_id), log_callback=self.log)',
    'cb = self.get_progress_callback(addon_id)\n                downloader.install_addon(int(addon_id), log_callback=self.log, progress_callback=cb)'
)

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
