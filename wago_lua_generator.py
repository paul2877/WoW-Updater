import os
import re

def add_wago_to_companion(addons_path, slug, name, encoded_string, author, version="1.0"):
    wa_comp_dir = os.path.join(addons_path, "WeakAurasCompanion")
    os.makedirs(wa_comp_dir, exist_ok=True)
    
    toc_path = os.path.join(wa_comp_dir, "WeakAurasCompanion.toc")
    if not os.path.exists(toc_path):
        with open(toc_path, "w", encoding="utf-8") as f:
            f.write("## Interface: 110002\n")
            f.write("## Title: WeakAuras Companion\n")
            f.write("## Author: WoW Updater\n")
            f.write("## Version: 1.0\n")
            f.write("## LoadOnDemand: 0\n")
            f.write("## DefaultState: enabled\n")
            f.write("## Dependencies: WeakAuras\n")
            f.write("data.lua\n")
            f.write("init.lua\n")

    init_path = os.path.join(wa_comp_dir, "init.lua")
    if not os.path.exists(init_path):
        with open(init_path, "w", encoding="utf-8") as f:
            f.write("WeakAurasCompanion = WeakAurasCompanion or {}\n")
            f.write("WeakAurasCompanion.stash = WeakAurasCompanion.stash or {}\n")

    data_path = os.path.join(wa_comp_dir, "data.lua")
    
    # Escape strings for Lua
    def escape_lua_str(s):
        if not s: return ""
        return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")

    lua_entry = f'''
WeakAurasCompanion.stash["{escape_lua_str(slug)}"] = {{
    ["name"] = "{escape_lua_str(name)}",
    ["encoded"] = "{escape_lua_str(encoded_string)}",
    ["author"] = "{escape_lua_str(author)}",
    ["version"] = "{escape_lua_str(version)}"
}}
'''
    
    existing_content = ""
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            existing_content = f.read()
            
    # We will just append our entry to the end. Since WeakAurasCompanion.stash is global, appending works perfectly.
    # But we need to make sure WeakAurasCompanion and stash exist.
    if "WeakAurasCompanion =" not in existing_content:
        with open(data_path, "w", encoding="utf-8") as f:
            f.write("WeakAurasCompanion = { stash = {} }\n")
            f.write(lua_entry)
    else:
        with open(data_path, "a", encoding="utf-8") as f:
            f.write(lua_entry)
            
    return True

def get_installed_wagos(addons_path):
    data_path = os.path.join(addons_path, "WeakAurasCompanion", "data.lua")
    if not os.path.exists(data_path):
        return []
        
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        results = []
        # Pattern to match: WeakAurasCompanion.stash["slug"] = { ... }
        pattern = r'WeakAurasCompanion\.stash\["([^"]+)"\]\s*=\s*\{(.*?)\}'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            slug = match.group(1)
            block = match.group(2)
            
            name_match = re.search(r'\["name"\]\s*=\s*"([^"]+)"', block)
            author_match = re.search(r'\["author"\]\s*=\s*"([^"]+)"', block)
            
            name = name_match.group(1) if name_match else "Unknown"
            author = author_match.group(1) if author_match else "Unknown"
            
            results.append({
                "slug": slug,
                "name": name,
                "author": author
            })
            
        return results
    except Exception as e:
        print(f"Error reading installed wagos: {e}")
        return []

def remove_wago(addons_path, target_slug):
    data_path = os.path.join(addons_path, "WeakAurasCompanion", "data.lua")
    if not os.path.exists(data_path):
        return False
        
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Pattern to match the specific block to remove
        pattern = r'WeakAurasCompanion\.stash\["' + re.escape(target_slug) + r'"\]\s*=\s*\{.*?\}'
        
        new_content = re.sub(pattern, "", content, flags=re.DOTALL)
        
        with open(data_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        return True
    except Exception as e:
        print(f"Error removing wago: {e}")
        return False
