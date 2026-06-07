import os

def adjust_offset():
    html_path = "../sentinel_ui_preview.html"
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        return
        
    with open(html_path, "r") as f:
        content = f.read()
        
    # Replace the -46px offset with the mathematically balanced -32px offset
    old_header = 'left: -46px;'
    new_header = 'left: -32px;'
    
    if old_header in content:
        content = content.replace(old_header, new_header)
        print("Successfully adjusted offset to -32px!")
    else:
        print("Error: Could not locate the -46px offset in the HTML content.")
        return
        
    with open(html_path, "w") as f:
        f.write(content)
        
    print("Adjustment complete!")

if __name__ == "__main__":
    adjust_offset()
