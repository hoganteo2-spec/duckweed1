#!/usr/bin/env python3
"""
Water Container Detection Module
Detects circular or oval water containers using edge detection and contour analysis.
Returns binary water mask and container metadata.
"""

import cv2
import numpy as np
import logging
from pathlib import Path
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)


def detect_water_container(image: np.ndarray, debug: bool = False) -> Dict:
    """
    Detect water container in image and return water mask.
    
    Supports:
    - Circular containers (using Hough Circle Detection)
    - Oval/elliptical containers (using contour fitting)
    - Rectangular containers (using contour fitting)
    
    Args:
        image: Input BGR image from OpenCV
        debug: If True, returns intermediate images for visualization
        
    Returns:
        Dictionary containing:
            - 'water_mask': Binary mask (0=background, 255=water)
            - 'container_type': 'circle', 'ellipse', or 'polygon'
            - 'center': (x, y) center point
            - 'radius': Radius (for circles) or equivalent
            - 'area': Water area in pixels
            - 'contour': Detected contour points
            - 'debug_images': (optional) Intermediate processing images
    """
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (7, 7), 1.5)
    
    # Step 1: Try to detect circular containers using Hough Circle Detection
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,           # Inverse ratio of accumulator resolution
        minDist=100,      # Minimum distance between circles
        param1=50,        # Upper Canny threshold
        param2=45,        # Accumulator threshold
        minRadius=80,     # Minimum radius
        maxRadius=500     # Maximum radius
    )
    
    debug_images = {}
    
    if circles is not None and len(circles[0]) > 0:
        # Circle detected - use Hough Circle result
        circle = circles[0][0]
        center_x, center_y, radius = int(circle[0]), int(circle[1]), int(circle[2])
        
        # Create water mask from circle
        water_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.circle(water_mask, (center_x, center_y), radius, 255, -1)
        
        logger.info(f"Detected circular container: center=({center_x}, {center_y}), radius={radius}")
        
        if debug:
            debug_img = image.copy()
            cv2.circle(debug_img, (center_x, center_y), radius, (0, 255, 0), 3)
            debug_images['hough_circles'] = debug_img
        
        return {
            'water_mask': water_mask,
            'container_type': 'circle',
            'center': (center_x, center_y),
            'radius': radius,
            'area': np.sum(water_mask > 0),
            'contour': np.array([]),
            'debug_images': debug_images if debug else {}
        }
    
    # Step 2: If circle detection failed, use contour-based detection
    # Apply Canny edge detection
    edges = cv2.Canny(blurred, 50, 150)
    
    # Dilate edges to close small gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    edges = cv2.dilate(edges, kernel, iterations=2)
    
    if debug:
        debug_images['edges'] = edges
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        logger.warning("No contours found - using full image as water region")
        water_mask = np.ones(image.shape[:2], dtype=np.uint8) * 255
        return {
            'water_mask': water_mask,
            'container_type': 'full_image',
            'center': (image.shape[1] // 2, image.shape[0] // 2),
            'radius': min(image.shape[:2]) // 2,
            'area': np.sum(water_mask > 0),
            'contour': np.array([]),
            'debug_images': debug_images if debug else {}
        }
    
    # Find the largest contour (assuming it's the water container)
    largest_contour = max(contours, key=cv2.contourArea)
    contour_area = cv2.contourArea(largest_contour)
    
    # Filter by area (must be significant portion of image)
    image_area = image.shape[0] * image.shape[1]
    min_area_ratio = 0.05  # At least 5% of image
    
    if contour_area < image_area * min_area_ratio:
        logger.warning("Detected contour too small - using full image")
        water_mask = np.ones(image.shape[:2], dtype=np.uint8) * 255
        return {
            'water_mask': water_mask,
            'container_type': 'full_image',
            'center': (image.shape[1] // 2, image.shape[0] // 2),
            'radius': min(image.shape[:2]) // 2,
            'area': np.sum(water_mask > 0),
            'contour': largest_contour,
            'debug_images': debug_images if debug else {}
        }
    
    # Try to fit ellipse to contour (for oval containers)
    if len(largest_contour) >= 5:
        ellipse = cv2.fitEllipse(largest_contour)
        center, (major_axis, minor_axis), angle = ellipse
        center = (int(center[0]), int(center[1]))
        
        # Create water mask from ellipse
        water_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.ellipse(water_mask, ellipse, 255, -1)
        
        logger.info(f"Detected oval container: center={center}, axes=({major_axis}, {minor_axis})")
        
        if debug:
            debug_img = image.copy()
            cv2.ellipse(debug_img, ellipse, (0, 255, 0), 3)
            debug_images['fitted_ellipse'] = debug_img
        
        return {
            'water_mask': water_mask,
            'container_type': 'ellipse',
            'center': center,
            'radius': int(max(major_axis, minor_axis) / 2),
            'area': np.sum(water_mask > 0),
            'contour': largest_contour,
            'debug_images': debug_images if debug else {}
        }
    else:
        # Fall back to contour-based mask
        water_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.drawContours(water_mask, [largest_contour], -1, 255, -1)
        
        # Get approximate center
        M = cv2.moments(largest_contour)
        if M['m00'] != 0:
            center_x = int(M['m10'] / M['m00'])
            center_y = int(M['m01'] / M['m00'])
        else:
            center_x, center_y = image.shape[1] // 2, image.shape[0] // 2
        
        logger.info(f"Detected polygon container: center=({center_x}, {center_y})")
        
        return {
            'water_mask': water_mask,
            'container_type': 'polygon',
            'center': (center_x, center_y),
            'radius': int(np.sqrt(contour_area / np.pi)),
            'area': np.sum(water_mask > 0),
            'contour': largest_contour,
            'debug_images': debug_images if debug else {}
        }


def refine_water_mask(water_mask: np.ndarray, image: np.ndarray) -> np.ndarray:
    """
    Refine water mask by removing noise and small artifacts.
    
    Args:
        water_mask: Binary water mask from detect_water_container()
        image: Original image (for context)
        
    Returns:
        Refined water mask
    """
    # Apply morphological operations to clean up mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    
    # Close small holes
    refined_mask = cv2.morphologyEx(water_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Remove small noise
    refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    return refined_mask


def validate_water_mask(water_mask: np.ndarray, image: np.ndarray) -> bool:
    """
    Validate if detected water mask is reasonable.
    
    Args:
        water_mask: Binary water mask
        image: Original image
        
    Returns:
        True if mask is valid, False otherwise
    """
    water_area = np.sum(water_mask > 0)
    total_area = water_mask.size
    
    # Water region should be between 10% and 90% of image
    water_ratio = water_area / total_area
    
    if water_ratio < 0.10 or water_ratio > 0.90:
        logger.warning(f"Water area ratio {water_ratio:.2%} seems unreasonable")
        return False
    
    return True


def save_water_mask(water_mask: np.ndarray, output_path: Path) -> None:
    """Save water mask to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    success = cv2.imwrite(str(output_path), water_mask)
    if not success:
        raise IOError(f"Failed to save water mask to {output_path}")
    logger.info(f"Saved water mask to {output_path}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    test_image_path = Path("duckweed_images") / "image.png"
    if test_image_path.exists():
        image = cv2.imread(str(test_image_path))
        result = detect_water_container(image, debug=True)
        print(f"Container type: {result['container_type']}")
        print(f"Center: {result['center']}")
        print(f"Radius: {result['radius']}")
        print(f"Water area: {result['area']} pixels")
