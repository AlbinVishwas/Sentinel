import cv2
import numpy as np
import os

def vectorize():
    # Read the logo image in grayscale
    img_path = "../frontend/public/logo.jpg"
    if not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        return
        
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    
    # Threshold the image to binary (invert because background is white)
    _, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("Error: No contours found.")
        return

    # Find the bounding box of all contours combined to center and scale
    all_pts = np.vstack(contours)
    x, y, w, h = cv2.boundingRect(all_pts)
    
    # Target coordinate space (100x100 box, centered at 50, 50 with margin)
    target_size = 80.0
    scale = target_size / max(w, h)
    
    # Centering calculations
    cx = x + w / 2.0
    cy = y + h / 2.0
    
    svg_paths = []
    
    for c in contours:
        # Simplify contour to keep curves smooth but remove jagged pixel steps
        # epsilon parameter controls approximation accuracy (smaller = closer to original)
        approx = cv2.approxPolyDP(c, 0.4, True)
        
        path_data = []
        for i, pt in enumerate(approx):
            px, py = pt[0]
            # Translate to origin, scale, and center at (50, 50)
            sx = (px - cx) * scale + 50.0
            sy = (py - cy) * scale + 50.0
            
            if i == 0:
                path_data.append(f"M{sx:.2f} {sy:.2f}")
            else:
                path_data.append(f"L{sx:.2f} {sy:.2f}")
        path_data.append("Z")
        svg_paths.append(" ".join(path_data))
        
    # Generate SVG content
    svg_content = '<?xml version="1.0" encoding="utf-8"?>\n'
    svg_content += '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="currentColor">\n'
    for path in svg_paths:
        svg_content += f'  <path d="{path}" />\n'
    svg_content += '</svg>\n'
    
    # Save SVG versions
    out_dir = "../frontend/public"
    os.makedirs(out_dir, exist_ok=True)
    
    # Standard logo.svg with fill="currentColor"
    with open(os.path.join(out_dir, "logo.svg"), "w") as f:
        f.write(svg_content)
        
    # Explicit logo_white.svg with fill="#ffffff"
    svg_white = svg_content.replace('fill="currentColor"', 'fill="#ffffff"')
    with open(os.path.join(out_dir, "logo_white.svg"), "w") as f:
        f.write(svg_white)
        
    print("Logo vectorized successfully! Created logo.svg and logo_white.svg.")

if __name__ == "__main__":
    vectorize()
