import os
import re

def align():
    html_path = "../sentinel_ui_preview.html"
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        return
        
    with open(html_path, "r") as f:
        content = f.read()
        
    # We will locate the empty-logo-badge-container and the h1 element
    # and replace them with a combined horizontal flex header
    pattern = r'(<!-- Stylied Center Logo -->\s*<div class="empty-logo-badge-container"[^>]*>.*?<svg[^>]*>(.*?)</svg>\s*</div>\s*<!-- Large Aesthetically-positioned Name -->\s*<h1>Sentinel</h1>)'
    
    # We use re.DOTALL to match across lines
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("Error: Could not locate the center logo and h1 name block in the HTML.")
        return
        
    svg_paths = match.group(2).strip()
    
    new_header = f"""<!-- Horizontal Header: Logo + Name aligned -->
          <div class="empty-header" style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <div class="empty-logo-badge-container" style="width: 28px; height: 28px; color: var(--color-text); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="currentColor" style="width: 100%; height: 100%;">
                {svg_paths}
              </svg>
            </div>
            <h1 style="font-size: 28px; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 0; line-height: 1;">Sentinel</h1>
          </div>"""
          
    # Replace in content
    updated_content = content.replace(match.group(1), new_header)
    
    with open(html_path, "w") as f:
        f.write(updated_content)
        
    print("Successfully aligned the logo to the left of the word 'Sentinel' in the empty state!")

if __name__ == "__main__":
    align()
