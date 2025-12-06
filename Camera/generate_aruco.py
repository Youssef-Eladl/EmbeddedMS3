"""
Generate ArUco markers for testing
"""
import cv2
import numpy as np

# ArUco dictionary
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

# Generate markers (IDs 0-9)
for marker_id in range(10):
    # Create marker image (200x200 pixels)
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, 200)
    
    # Add white border for printing
    marker_with_border = cv2.copyMakeBorder(marker_image, 20, 20, 20, 20, 
                                            cv2.BORDER_CONSTANT, value=255)
    
    # Add ID label
    cv2.putText(marker_with_border, f"ID: {marker_id}", (10, 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 2)
    
    # Save marker
    filename = f"aruco_marker_{marker_id}.png"
    cv2.imwrite(filename, marker_with_border)
    print(f"Generated: {filename}")

print("\nDone! Print these markers or display them on your phone to test.")
