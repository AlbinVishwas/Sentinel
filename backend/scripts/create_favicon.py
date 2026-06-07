import cv2
import numpy as np
from PIL import Image
import os

def generate_favicons():
    # 1. Generate icon.svg for modern browsers
    svg_src_path = "../frontend/public/logo_white.svg"
    svg_dest_path = "../frontend/src/app/icon.svg"
    
    if os.path.exists(svg_src_path):
        with open(svg_src_path, "r") as f:
            svg_content = f.read()
        with open(svg_dest_path, "w") as f:
            f.write(svg_content)
        print("Created icon.svg in app directory.")
    else:
        print("Error: logo_white.svg not found.")
        
    # 2. Rasterize logo to 32x32 and save as favicon.ico
    img_jpg_path = "../frontend/public/logo.jpg"
    if not os.path.exists(img_jpg_path):
        print(f"Error: {img_jpg_path} not found.")
        return
        
    # Read logo in grayscale
    img = cv2.imread(img_jpg_path, cv2.IMREAD_GRAYSCALE)
    _, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Render onto a high-res canvas (e.g. 256x256) for smooth downscaling (anti-aliasing)
    canvas_size = 256
    canvas = np.zeros((canvas_size, canvas_size, 4), dtype=np.uint8) # RGBA
    
    all_pts = np.vstack(contours)
    x, y, w, h = cv2.boundingRect(all_pts)
    
    # Scale to fit with margin
    target_size = canvas_size * 0.8
    scale = target_size / max(w, h)
    
    cx = x + w / 2.0
    cy = y + h / 2.0
    
    # Transform and draw contours
    transformed_contours = []
    for c in contours:
        tc = np.zeros_like(c)
        for i, pt in enumerate(c):
            px, py = pt[0]
            sx = (px - cx) * scale + (canvas_size / 2.0)
            sy = (py - cy) * scale + (canvas_size / 2.0)
            tc[i] = [int(round(sx)), int(round(sy))]
        transformed_contours.append(tc)
        
    # Draw solid white shapes
    cv2.fillPoly(canvas, transformed_contours, (255, 255, 255, 255))
    
    # Convert numpy RGBA array to PIL Image
    pil_img = Image.fromarray(canvas, 'RGBA')
    
    # Downscale to 32x32 with high-quality Lanczos filter for smooth edges
    ico_size = (32, 32)
    ico_img = pil_img.resize(ico_size, Image.Resampling.LANCZOS)
    
    # Save as favicon.ico in Next.js app folder (overwrite existing)
    ico_dest_path = "../frontend/src/app/favicon.ico"
    ico_img.save(ico_dest_path, format="ICO")
    print(f"Overwrote favicon.ico at {ico_dest_path} with the new design.")

if __name__ == "__main__":
    generate_favicons()
