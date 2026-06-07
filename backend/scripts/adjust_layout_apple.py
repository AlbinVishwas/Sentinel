import os
import re

def adjust():
    html_path = "../sentinel_ui_preview.html"
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        return
        
    with open(html_path, "r") as f:
        content = f.read()
        
    # 1. Update font-family stacks in the <style> block to prioritize SF Pro Display
    content = content.replace(
        'font-family: \'Inter\', -apple-system, sans-serif;',
        'font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;'
    )
    
    # 2. Update h1 font configuration in style block if present
    content = re.sub(
        r'\.empty-state h1\s*\{([^}]+)\}',
        r'.empty-state h1 {\n      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;\n      font-size: 64px;\n      font-weight: 600;\n      letter-spacing: -0.045em;\n      margin-bottom: 0;\n      color: var(--color-text);\n      line-height: 1;\n    }',
        content
    )
    
    # 3. Locate the empty-header container in body and apply exact sizes & spacing
    header_pattern = r'<div class="empty-header"[^>]*>.*?<div class="empty-logo-badge-container"[^>]*>(.*?)</div>\s*<h1[^>]*>Sentinel</h1>\s*</div>'
    match = re.search(header_pattern, content, re.DOTALL)
    if not match:
        print("Error: Could not locate empty-header in HTML body.")
        return
        
    svg_block = match.group(1).strip()
    
    new_header = f"""<div class="empty-header" style="display: flex; align-items: center; justify-content: center; gap: 24px; margin-bottom: 24px;">
            <div class="empty-logo-badge-container" style="width: 64px; height: 64px; color: var(--color-text); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
              {svg_block}
            </div>
            <h1 style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif; font-size: 64px; font-weight: 600; letter-spacing: -0.045em; margin-bottom: 0; line-height: 1;">Sentinel</h1>
          </div>"""
          
    updated_content = content.replace(match.group(0), new_header)
    
    # 4. Also adjust the subhead margin for spacing balance
    updated_content = updated_content.replace(
        '.empty-state p {\n      font-size: 13.5px;\n      color: var(--color-muted);\n      line-height: 1.5;\n      margin-bottom: 32px;\n      max-width: 400px;\n    }',
        '.empty-state p {\n      font-size: 13.5px;\n      color: var(--color-muted);\n      line-height: 1.5;\n      margin-bottom: 36px;\n      max-width: 420px;\n    }'
    )
    
    with open(html_path, "w") as f:
        f.write(updated_content)
        
    print("Successfully updated typography to SF Pro Display and applied exact logo size/spacing ratios!")

if __name__ == "__main__":
    adjust()
