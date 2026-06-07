import re

with open("gui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove the __main__ block
main_block = """if __name__ == "__main__":
    app = App()
    app.mainloop()
"""
content = content.replace(main_block, "")

# Ensure all new functions are indented properly as class methods
# They were already indented with 4 spaces in the patch files, so they should be fine as long as they are inside the class.
# We just need to append the main block at the very end.

content = content + "\n" + main_block

with open("gui.py", "w", encoding="utf-8") as f:
    f.write(content)
