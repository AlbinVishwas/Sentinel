import os
import re

def resize():
    html_path = "../sentinel_ui_preview.html"
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        return
        
    with open(html_path, "r") as f:
        content = f.read()
        
    # 1. Update the stylesheet rule for .empty-state h1
    content = re.sub(
        r'\.empty-state h1\s*\{([^}]+)\}',
        r'.empty-state h1 {\n      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;\n      font-size: 32px;\n      font-weight: 600;\n      letter-spacing: -0.03em;\n      margin-bottom: 0;\n      color: var(--color-text);\n      line-height: 1;\n    }',
        content
    )
    
    # 2. Update the HTML empty-header block to use the compact sizing (32px logo, 32px text, 12px gap, 16px margin)
    header_pattern = r'<div class="empty-header"[^>]*>.*?<div class="empty-logo-badge-container"[^>]*>(.*?)</div>\s*<h1[^>]*>Sentinel</h1>\s*</div>'
    match = re.search(header_pattern, content, re.DOTALL)
    if not match:
        print("Error: Could not locate empty-header in HTML body.")
        return
        
    svg_block = match.group(1).strip()
    
    new_header = f"""<div class="empty-header" style="display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 16px;">
            <div class="empty-logo-badge-container" style="width: 32px; height: 32px; color: var(--color-text); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
              {svg_block}
            </div>
            <h1 style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif; font-size: 32px; font-weight: 600; letter-spacing: -0.03em; margin-bottom: 0; line-height: 1;">Sentinel</h1>
          </div>"""
          
    updated_content = content.replace(match.group(0), new_header)
    
    # 3. Update the description margin to keep it compact
    updated_content = updated_content.replace(
        '.empty-state p {\n      font-size: 13.5px;\n      color: var(--color-muted);\n      line-height: 1.5;\n      margin-bottom: 36px;\n      max-width: 420px;\n    }',
        '.empty-state p {\n      font-size: 13.5px;\n      color: var(--color-muted);\n      line-height: 1.5;\n      margin-bottom: 24px;\n      max-width: 420px;\n    }'
    )
    
    with open(html_path, "w") as f:
        f.write(updated_content)
        
    print("Successfully resized empty state elements and aligned centering!")

if __name__ == "__main__":
    resize()
