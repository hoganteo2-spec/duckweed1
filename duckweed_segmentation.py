#!/usr/bin/env python3
"""
Enhanced Duckweed Segmentation Module
High-accuracy green color segmentation with advanced filtering and noise removal.
"""

import cv2
import numpy as np
import logging
from pathlib import Path
from typing import Tuple, Dict

logger = logging.getLogger(__name__)


def create_duckweed_mask(image: np.ndarray, water_mask: np.ndarray, debug: bool = False) -> Dict:
    """
    Create duckweed mask using HSV color segmentation.
    Handles shadows, reflections, and varying lighting conditions.
    
    Args:
        image: Input BGR image
        water_mask: Binary water mask (255=water, 0=background)
        debug: If True, return intermediate images
        
    Returns:
        Dictionary containing:
            - 'raw_mask': Raw HSV-based mask
            - 'cleaned_mask': After noise removal
            - 'final_mask': Final duckweed mask
            - 'debug_images': Intermediate processing images
    """
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(image, (9, 9), 1.0)
    
    # Convert BGR to HSV
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    
    debug_images = {}
    
    # Define HSV ranges for green duckweed
    # Duckweed is typically a darker, saturated green
    # Hue: 30-90 (green range), Saturation: 40-255 (medium to high), Value: 40-220 (not too bright/dark)
    lower_green = np.array([30, 60, 40], dtype=np.uint8)
    upper_green = np.array([95, 255, 220], dtype=np.uint8)
    
    # Create initial green mask
    green_mask = cv2.inRange(hsv, lower_green, upper_green)
    
    if debug:
        debug_images['hsv_green'] = green_mask
    
    # Step 1: Remove bright reflections (high value pixels with low saturation)
    value_channel = hsv[:, :, 2]
    saturation_channel = hsv[:, :, 1]
    
    # Reflections are bright (V > 220) OR very desaturated (S < 40)
    reflection_mask = (value_channel > 220) | (saturation_channel < 40)
    green_mask[reflection_mask] = 0
    
    # Step 2: Remove very dark pixels (shadow artifacts)
    # Keep pixels with value > 30 to filter out shadows
    dark_mask = value_channel < 30
    green_mask[dark_mask] = 0
    
    if debug:
        debug_images['after_reflection_removal'] = green_mask
    
    # Step 3: Apply morphological operations to clean up mask
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    
    # Opening: remove small noise
    cleaned_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel_small, iterations=1)
    
    # Closing: fill small holes in duckweed
    cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel_medium, iterations=1)
    
    if debug:
        debug_images['after_morphology'] = cleaned_mask
    
    # Step 4: Filter by contour area - remove very small isolated pixels
    # This helps with scattered noise and floating debris
    contours, _ = cv2.findContours(cleaned_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Determine minimum contour area based on image size
    image_area = image.shape[0] * image.shape[1]
    min_contour_area = int(image_area * 0.0001)  # 0.01% of image
    max_contour_area = image_area  # No upper limit
    
    final_mask = np.zeros_like(cleaned_mask)
    valid_contours = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_contour_area <= area <= max_contour_area:
            cv2.drawContours(final_mask, [contour], -1, 255, thickness=cv2.FILLED)
            valid_contours.append(contour)
    
    if debug:
        debug_images['after_contour_filtering'] = final_mask
    
    # Step 5: Clip to water region only
    # Ensure duckweed is only counted within the water mask
    final_mask = cv2.bitwise_and(final_mask, water_mask)
    
    if debug:
        debug_images['clipped_to_water'] = final_mask
    
    logger.info(f"Duckweed mask created: {np.sum(final_mask > 0)} pixels detected")
    
    return {
        'raw_mask': green_mask,
        'cleaned_mask': cleaned_mask,
        'final_mask': final_mask,
        'contours': valid_contours,
        'debug_images': debug_images if debug else {}
    }


def calculate_coverage(duckweed_mask: np.ndarray, water_mask: np.ndarray) -> Tuple[float, int, int]:
    """
    Calculate duckweed coverage percentage within water region.
    
    Formula: (duckweed pixels inside water / total water pixels) × 100
    
    Args:
        duckweed_mask: Binary duckweed mask
        water_mask: Binary water mask
        
    Returns:
        Tuple of (coverage_percent, duckweed_pixels, water_pixels)
    """
    water_pixels = int(np.count_nonzero(water_mask))
    duckweed_pixels = int(np.count_nonzero(duckweed_mask))
    
    if water_pixels == 0:
        logger.warning("No water region detected - coverage cannot be calculated")
        return 0.0, 0, 0
    
    coverage = (duckweed_pixels / water_pixels) * 100.0
    coverage = round(coverage, 2)
    
    logger.info(f"Coverage calculated: {coverage}% ({duckweed_pixels}/{water_pixels} pixels)")
    
    return coverage, duckweed_pixels, water_pixels


def build_segmented_image(image: np.ndarray, duckweed_mask: np.ndarray, 
                         water_mask: np.ndarray, coverage: float) -> np.ndarray:
    """
    Build overlay image with duckweed highlighted in green.
    
    Args:
        image: Original BGR image
        duckweed_mask: Binary duckweed mask
        water_mask: Binary water mask
        coverage: Coverage percentage for annotation
        
    Returns:
        Annotated image with duckweed highlighted
    """
    # Create overlay with duckweed in bright green
    overlay = image.copy()
    overlay[duckweed_mask > 0] = [0, 255, 0]  # Bright green for duckweed
    
    # Blend original and overlay
    highlighted = cv2.addWeighted(image, 0.6, overlay, 0.4, 0)
    
    # Draw water boundary in red
    contours, _ = cv2.findContours(water_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        cv2.drawContours(highlighted, contours, -1, (0, 0, 255), 2)
    
    # Add coverage text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    thickness = 2
    text = f"Coverage: {coverage:.2f}%"
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    
    # Add background rectangle for text readability
    x, y = 10, 30
    cv2.rectangle(highlighted, (x - 5, y - text_size[1] - 5), 
                  (x + text_size[0] + 5, y + 5), (0, 0, 0), -1)
    cv2.rectangle(highlighted, (x - 5, y - text_size[1] - 5), 
                  (x + text_size[0] + 5, y + 5), (255, 255, 255), 2)
    
    # Put coverage text
    cv2.putText(highlighted, text, (x, y), font, font_scale, (0, 255, 0), thickness)
    
    return highlighted


def build_contour_image(image: np.ndarray, duckweed_mask: np.ndarray, 
                       water_mask: np.ndarray, coverage: float) -> np.ndarray:
    """
    Build contour visualization image.
    
    Args:
        image: Original BGR image
        duckweed_mask: Binary duckweed mask
        water_mask: Binary water mask
        coverage: Coverage percentage
        
    Returns:
        Image with duckweed contours drawn
    """
    contour_img = image.copy()
    
    # Draw duckweed contours in green
    duckweed_contours, _ = cv2.findContours(duckweed_mask.copy(), 
                                            cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(contour_img, duckweed_contours, -1, (0, 255, 0), 2)
    
    # Draw water boundary in red
    water_contours, _ = cv2.findContours(water_mask.copy(), 
                                         cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(contour_img, water_contours, -1, (0, 0, 255), 3)
    
    # Add coverage text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    thickness = 2
    text = f"Coverage: {coverage:.2f}%"
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    
    x, y = 10, 30
    cv2.rectangle(contour_img, (x - 5, y - text_size[1] - 5), 
                  (x + text_size[0] + 5, y + 5), (0, 0, 0), -1)
    cv2.rectangle(contour_img, (x - 5, y - text_size[1] - 5), 
                  (x + text_size[0] + 5, y + 5), (255, 255, 255), 2)
    cv2.putText(contour_img, text, (x, y), font, font_scale, (0, 255, 0), thickness)
    
    return contour_img


def save_masks(output_dir: Path, image_name: str, water_mask: np.ndarray, 
               duckweed_mask: np.ndarray, segmented_img: np.ndarray, 
               contour_img: np.ndarray) -> Dict[str, Path]:
    """
    Save all output masks and images to disk.
    
    Args:
        output_dir: Base output directory
        image_name: Original image filename (for naming outputs)
        water_mask: Binary water mask
        duckweed_mask: Binary duckweed mask
        segmented_img: Segmented overlay image
        contour_img: Contour visualization image
        
    Returns:
        Dictionary with paths to all saved files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    water_dir = output_dir / "water_masks"
    duckweed_dir = output_dir / "duckweed_masks"
    contour_dir = output_dir / "contours"
    annotated_dir = output_dir / "annotated"
    
    for subdir in [water_dir, duckweed_dir, contour_dir, annotated_dir]:
        subdir.mkdir(parents=True, exist_ok=True)
    
    # Prepare output filename without extension
    base_name = Path(image_name).stem
    
    # Save masks
    water_path = water_dir / f"{base_name}_water_mask.png"
    duckweed_path = duckweed_dir / f"{base_name}_duckweed_mask.png"
    contour_path = contour_dir / f"{base_name}_contours.png"
    segmented_path = annotated_dir / f"{base_name}_segmented.png"
    
    cv2.imwrite(str(water_path), water_mask)
    cv2.imwrite(str(duckweed_path), duckweed_mask)
    cv2.imwrite(str(contour_path), contour_img)
    cv2.imwrite(str(segmented_path), segmented_img)
    
    logger.info(f"Saved water mask: {water_path}")
    logger.info(f"Saved duckweed mask: {duckweed_path}")
    logger.info(f"Saved contour image: {contour_path}")
    logger.info(f"Saved segmented image: {segmented_path}")
    
    return {
        'water_mask': water_path,
        'duckweed_mask': duckweed_path,
        'contours': contour_path,
        'segmented': segmented_path
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
