"""
Grid Template Generator
Creates a printable 5x5 grid image for the tracking system
Author: GitHub Copilot
Date: November 2025
"""

import cv2
import numpy as np

def generate_grid_template(output_file='grid_template.png'):
    """
    Generate a 5x5 grid template image for printing
    Creates a 2100x2100 pixel image (25cm at 210 DPI)
    """
    
    # Image parameters
    grid_size = 5
    cell_size = 420  # pixels per cell (5cm at 210 DPI)
    line_width = 12  # pixels (approximately 3mm)
    
    total_size = cell_size * grid_size
    
    # Create white background
    img = np.ones((total_size, total_size, 3), dtype=np.uint8) * 255
    
    # Draw vertical lines
    for i in range(grid_size + 1):
        x = i * cell_size
        cv2.line(img, (x, 0), (x, total_size), (0, 0, 0), line_width)
    
    # Draw horizontal lines
    for i in range(grid_size + 1):
        y = i * cell_size
        cv2.line(img, (0, y), (total_size, y), (0, 0, 0), line_width)
    
    # Add coordinate labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.5
    font_thickness = 3
    
    # Label columns (0-4) at top
    for col in range(grid_size):
        x = col * cell_size + cell_size // 2 - 15
        cv2.putText(img, str(col), (x, 40), font, font_scale, (0, 0, 0), font_thickness)
    
    # Label rows (0-4) at left
    for row in range(grid_size):
        y = row * cell_size + cell_size // 2 + 15
        cv2.putText(img, str(row), (20, y), font, font_scale, (0, 0, 0), font_thickness)
    
    # Add title
    title = "5x5 TRACKING GRID"
    title_font_scale = 2.0
    title_thickness = 4
    text_size = cv2.getTextSize(title, font, title_font_scale, title_thickness)[0]
    text_x = (total_size - text_size[0]) // 2
    text_y = total_size - 50
    
    # White background for title
    cv2.rectangle(img, (text_x - 20, text_y - text_size[1] - 10), 
                  (text_x + text_size[0] + 20, text_y + 10), (255, 255, 255), -1)
    
    cv2.putText(img, title, (text_x, text_y), font, title_font_scale, (0, 0, 0), title_thickness)
    
    # Add instructions at bottom
    instructions = [
        "Print at actual size (25cm x 25cm)",
        "Each cell: 5cm x 5cm",
        "Mount on flat, rigid surface"
    ]
    
    y_offset = total_size + 100
    for i, instruction in enumerate(instructions):
        cv2.putText(img, instruction, (50, y_offset + i * 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # Save image
    cv2.imwrite(output_file, img)
    print(f"Grid template saved as '{output_file}'")
    print(f"Image size: {total_size}x{total_size} pixels")
    print(f"Recommended print size: 25cm x 25cm")
    print(f"\nPrinting Instructions:")
    print("1. Open the image in an image viewer or printer software")
    print("2. Select 'Print' and choose 'Actual Size' or '100% scale'")
    print("3. Verify the printed grid is 25cm x 25cm")
    print("4. Mount on cardboard or foam board for rigidity")
    
    # Create a preview (smaller version for display)
    preview_size = 800
    preview = cv2.resize(img, (preview_size, preview_size))
    cv2.imshow('Grid Template Preview', preview)
    print("\nPress any key to close preview window...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    generate_grid_template()
