import os

target = "patreon.com/weakauras"
path = r"D:\The War Within"

found = []
for root, dirs, files in os.walk(path):
    for f in files:
        if f.endswith(".lua") or f.endswith(".toc") or f.endswith(".txt"):
            filepath = os.path.join(root, f)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    if target.lower() in content.lower():
                        found.append(filepath)
                        print(f"Found in {filepath}")
            except Exception as e:
                pass
print("Done searching.")
