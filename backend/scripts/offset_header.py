import os
import re

def offset_header():
    html_path = "../sentinel_ui_preview.html"
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        return
        
    with open(html_path, "r") as f:
        content = f.read()
        
    # Locate empty-header block and apply the position relative with left -46px offset
    old_header_start = '<div class="empty-header" style="display: flex; align-items: center; justify-content: center; gap: 16px; margin-bottom: 20px;">'
    new_header_start = '<div class="empty-header" style="display: flex; align-items: center; justify-content: center; gap: 16px; margin-bottom: 20px; position: relative; left: -46px;">'
    
    if old_header_start in content:
        content = content.replace(old_header_start, new_header_start)
        print("Successfully applied 46px offset to empty header!")
    else:
        # Try finding using regex just in case
        pattern = r'<div class="empty-header"[^>]*style="[^"]*">'
        match = re.search(pattern, content)
        if match:
            content = content.replace(match.group(0), new_header_start)
            print("Successfully applied 46px offset to empty header via regex!")
        else:
            print("Error: Could not locate empty-header in HTML body.")
            return
            
    with open(html_path, "w") as f:
        f.write(content)
        
    print("Alignment offset complete!")

if __name__ == "__main__":
    offset_header()
