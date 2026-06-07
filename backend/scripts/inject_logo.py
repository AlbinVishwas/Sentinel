import os

def inject():
    # Read logo.svg paths
    svg_path = "../frontend/public/logo.svg"
    if not os.path.exists(svg_path):
        print(f"Error: {svg_path} not found.")
        return
        
    with open(svg_path, "r") as f:
        svg_lines = f.readlines()
        
    # Extract path elements
    paths = []
    for line in svg_lines:
        if "<path" in line:
            paths.append(line.strip())
            
    paths_str = "\n      ".join(paths)
    
    # Define SVG wrappers
    header_svg = f"""<div class="logo-badge-container" style="width: 20px; height: 20px; color: var(--color-text); flex-shrink: 0; display: flex; align-items: center; justify-content: center;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="currentColor" style="width: 100%; height: 100%;">
        {paths_str}
      </svg>
    </div>"""

    center_svg = f"""<div class="empty-logo-badge-container" style="width: 48px; height: 48px; color: var(--color-text); display: flex; align-items: center; justify-content: center; margin-bottom: 20px;">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="currentColor" style="width: 100%; height: 100%;">
        {paths_str}
      </svg>
    </div>"""

    # Read sentinel_ui_preview.html
    html_path = "../sentinel_ui_preview.html"
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        return
        
    with open(html_path, "r") as f:
        html_content = f.read()
        
    # Replace header badge
    target_header = '<div class="logo-badge">S</div>'
    if target_header in html_content:
        html_content = html_content.replace(target_header, header_svg)
        print("Replaced logo badge in header.")
    else:
        print("Header badge target not found.")
        
    # Replace empty state badge
    target_center = '<div class="empty-logo-badge">S</div>'
    if target_center in html_content:
        html_content = html_content.replace(target_center, center_svg)
        print("Replaced center empty logo badge.")
    else:
        print("Center logo badge target not found.")
        
    # Write back
    with open(html_path, "w") as f:
        f.write(html_content)
        
    print("Injection finished successfully!")

if __name__ == "__main__":
    inject()
