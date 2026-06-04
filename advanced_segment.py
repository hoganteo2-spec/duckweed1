#!/usr/bin/env python3
"""
High-Accuracy Duckweed Segmentation System
Complete pipeline: water detection → duckweed detection → analysis → upload
"""

import argparse
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

import cv2
import numpy as np

import water_detection
import duckweed_segmentation
from gdrive_uploader import create_uploader, GoogleDriveUploader

# Configuration
DEFAULT_INPUT_DIR = Path("duckweed_images")
DEFAULT_OUTPUT_DIR = Path("segmented_images")
DEFAULT_RESULTS_FILE = Path("results.csv")
LOG_FILE = Path("segmentation.log")

# CSV header
RESULTS_CSV_HEADER = [
    "timestamp",
    "image_filename",
    "container_type",
    "water_area_pixels",
    "duckweed_pixels",
    "duckweed_coverage_percent",
    "gdrive_upload_status"
]


def setup_logging(log_file: Path = LOG_FILE):
    """Configure logging to stdout and file."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode='a', encoding='utf-8')
        ]
    )


def get_image_paths(image_dir: Path) -> List[Path]:
    """Get all supported image files from directory."""
    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")
    
    supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    image_paths = [
        p for p in sorted(image_dir.iterdir())
        if p.suffix.lower() in supported_formats
    ]
    
    if not image_paths:
        raise FileNotFoundError(f"No images found in {image_dir}")
    
    logging.info(f"Found {len(image_paths)} images in {image_dir}")
    return image_paths


def load_image(image_path: Path) -> np.ndarray:
    """Load image from disk."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise IOError(f"Failed to load image: {image_path}")
    return image


def process_single_image(
    image_path: Path,
    output_dir: Path,
    results_file: Path,
    uploader: Optional[GoogleDriveUploader] = None,
    enable_upload: bool = False,
    debug: bool = False
) -> Optional[Dict]:
    """
    Process a single image: detect water → detect duckweed → calculate coverage → save outputs.
    
    Args:
        image_path: Path to input image
        output_dir: Output directory for segmented images
        results_file: CSV file for results
        uploader: GoogleDriveUploader instance (optional)
        enable_upload: Whether to upload to Google Drive
        debug: If True, save debug images
        
    Returns:
        Dictionary with processing results, or None if failed
    """
    try:
        logging.info(f"\n{'='*80}")
        logging.info(f"Processing: {image_path.name}")
        logging.info(f"{'='*80}")
        
        # Load image
        image = load_image(image_path)
        image_height, image_width = image.shape[:2]
        logging.info(f"Image size: {image_width}x{image_height}")
        
        # Step 1: Detect water container
        logging.info("Step 1: Detecting water container...")
        water_result = water_detection.detect_water_container(image, debug=debug)
        water_mask = water_result['water_mask']
        container_type = water_result['container_type']
        water_area = water_result['area']
        
        logging.info(f"  Container type: {container_type}")
        logging.info(f"  Water area: {water_area} pixels")
        
        # Validate water mask
        if not water_detection.validate_water_mask(water_mask, image):
            logging.warning("Water mask validation failed - using full image")
        
        # Refine water mask
        water_mask = water_detection.refine_water_mask(water_mask, image)
        water_area = np.sum(water_mask > 0)
        logging.info(f"  Water area (refined): {water_area} pixels")
        
        # Step 2: Detect duckweed
        logging.info("Step 2: Detecting duckweed...")
        duckweed_result = duckweed_segmentation.create_duckweed_mask(image, water_mask, debug=debug)
        duckweed_mask = duckweed_result['final_mask']
        
        # Step 3: Calculate coverage
        logging.info("Step 3: Calculating coverage...")
        coverage, duckweed_pixels, _ = duckweed_segmentation.calculate_coverage(
            duckweed_mask, water_mask
        )
        logging.info(f"  Coverage: {coverage:.2f}%")
        logging.info(f"  Duckweed pixels: {duckweed_pixels}")
        
        # Step 4: Build output images
        logging.info("Step 4: Building output images...")
        segmented_img = duckweed_segmentation.build_segmented_image(
            image, duckweed_mask, water_mask, coverage
        )
        contour_img = duckweed_segmentation.build_contour_image(
            image, duckweed_mask, water_mask, coverage
        )
        
        # Step 5: Save outputs
        logging.info("Step 5: Saving output files...")
        output_paths = duckweed_segmentation.save_masks(
            output_dir,
            image_path.name,
            water_mask,
            duckweed_mask,
            segmented_img,
            contour_img
        )
        
        # Step 6: Append results to CSV
        logging.info("Step 6: Logging results...")
        timestamp = datetime.now().isoformat()
        append_results_csv(
            results_file,
            timestamp,
            image_path.name,
            container_type,
            water_area,
            duckweed_pixels,
            coverage,
            "pending"
        )
        
        # Step 7: Upload to Google Drive
        upload_status = "skipped"
        if enable_upload and uploader:
            logging.info("Step 7: Uploading to Google Drive...")
            
            files_to_upload = [
                output_paths['water_mask'],
                output_paths['duckweed_mask'],
                output_paths['contours'],
                output_paths['segmented']
            ]
            
            # Create subfolder with image name
            subfolder = Path(image_path.stem)
            
            all_success = True
            for file_path in files_to_upload:
                result = uploader.upload_file(file_path, subfolder=str(subfolder))
                if result is None:
                    all_success = False
            
            upload_status = "success" if all_success else "failed"
            logging.info(f"Upload status: {upload_status}")
        
        # Update CSV with upload status
        update_results_csv_upload_status(results_file, image_path.name, upload_status)
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"✓ Processing complete: {image_path.name}")
        print(f"  Container: {container_type}")
        print(f"  Water area: {water_area} pixels")
        print(f"  Duckweed: {duckweed_pixels} pixels")
        print(f"  Coverage: {coverage:.2f}%")
        print(f"  Upload: {upload_status}")
        print(f"  Output files:")
        print(f"    - {output_paths['water_mask']}")
        print(f"    - {output_paths['duckweed_mask']}")
        print(f"    - {output_paths['contours']}")
        print(f"    - {output_paths['segmented']}")
        print(f"{'='*80}\n")
        
        return {
            'image_path': image_path,
            'container_type': container_type,
            'water_area': water_area,
            'duckweed_pixels': duckweed_pixels,
            'coverage': coverage,
            'upload_status': upload_status,
            'output_paths': output_paths
        }
    
    except Exception as e:
        logging.exception(f"Error processing {image_path.name}: {str(e)}")
        print(f"✗ Error processing {image_path.name}: {str(e)}")
        
        # Log failed status
        try:
            timestamp = datetime.now().isoformat()
            append_results_csv(
                results_file,
                timestamp,
                image_path.name,
                "error",
                0,
                0,
                0.0,
                "failed"
            )
        except Exception as csv_err:
            logging.error(f"Failed to log error to CSV: {csv_err}")
        
        return None


def append_results_csv(
    results_file: Path,
    timestamp: str,
    image_filename: str,
    container_type: str,
    water_area: int,
    duckweed_pixels: int,
    coverage: float,
    upload_status: str
):
    """Append analysis results to CSV file."""
    file_exists = results_file.exists()
    
    with results_file.open('a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header if file is new
        if not file_exists or results_file.stat().st_size == 0:
            writer.writerow(RESULTS_CSV_HEADER)
        
        # Write data row
        writer.writerow([
            timestamp,
            image_filename,
            container_type,
            water_area,
            duckweed_pixels,
            coverage,
            upload_status
        ])
    
    logging.info(f"Appended results to {results_file}")


def update_results_csv_upload_status(results_file: Path, image_filename: str, upload_status: str):
    """Update upload status for most recent entry with given image filename."""
    try:
        # Read all rows
        rows = []
        with results_file.open('r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
        
        if not rows:
            return
        
        # Find and update last matching row
        for i in range(len(rows) - 1, 0, -1):  # Start from end, skip header
            if len(rows[i]) > 1 and rows[i][1] == image_filename:
                rows[i][-1] = upload_status  # Update last column (upload_status)
                break
        
        # Write all rows back
        with results_file.open('w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)
        
        logging.info(f"Updated upload status for {image_filename} to {upload_status}")
    
    except Exception as e:
        logging.error(f"Failed to update CSV upload status: {e}")


def process_all_images(
    input_dir: Path,
    output_dir: Path,
    results_file: Path,
    uploader: Optional[GoogleDriveUploader] = None,
    enable_upload: bool = False,
    debug: bool = False
) -> Dict[str, any]:
    """
    Process all images in input directory.
    
    Args:
        input_dir: Input directory with images
        output_dir: Output directory for results
        results_file: CSV results file
        uploader: GoogleDriveUploader instance
        enable_upload: Whether to upload to Google Drive
        debug: Debug mode
        
    Returns:
        Summary dictionary
    """
    image_paths = get_image_paths(input_dir)
    
    results = {
        'total': len(image_paths),
        'successful': 0,
        'failed': 0,
        'images': []
    }
    
    for idx, image_path in enumerate(image_paths, 1):
        print(f"\n[{idx}/{len(image_paths)}] Processing image: {image_path.name}")
        
        result = process_single_image(
            image_path,
            output_dir,
            results_file,
            uploader=uploader,
            enable_upload=enable_upload,
            debug=debug
        )
        
        if result:
            results['successful'] += 1
            results['images'].append(result)
        else:
            results['failed'] += 1
    
    return results


def print_summary(results: Dict):
    """Print processing summary."""
    print(f"\n{'='*80}")
    print("PROCESSING SUMMARY")
    print(f"{'='*80}")
    print(f"Total images: {results['total']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    
    if results['images']:
        print(f"\nCoverage Statistics:")
        coverages = [r['coverage'] for r in results['images']]
        print(f"  Min: {min(coverages):.2f}%")
        print(f"  Max: {max(coverages):.2f}%")
        print(f"  Avg: {sum(coverages) / len(coverages):.2f}%")
    
    print(f"\nResults saved to: {Path.cwd() / DEFAULT_RESULTS_FILE}")
    print(f"{'='*80}\n")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="High-accuracy duckweed segmentation system with Google Drive upload"
    )
    
    parser.add_argument(
        '--input-dir',
        default=str(DEFAULT_INPUT_DIR),
        help=f'Input directory with images (default: {DEFAULT_INPUT_DIR})'
    )
    
    parser.add_argument(
        '--output-dir',
        default=str(DEFAULT_OUTPUT_DIR),
        help=f'Output directory for segmented images (default: {DEFAULT_OUTPUT_DIR})'
    )
    
    parser.add_argument(
        '--csv',
        default=str(DEFAULT_RESULTS_FILE),
        help=f'CSV results file (default: {DEFAULT_RESULTS_FILE})'
    )
    
    parser.add_argument(
        '--single',
        help='Process a single image by path'
    )
    
    parser.add_argument(
        '--upload',
        action='store_true',
        help='Enable automatic upload to Google Drive'
    )
    
    parser.add_argument(
        '--credentials',
        help='Path to Google credentials file (service account or OAuth)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (save intermediate images)'
    )
    
    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='Disable Google Drive upload even if credentials available'
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    setup_logging()
    args = parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    results_file = Path(args.csv)
    
    # Initialize Google Drive uploader if needed
    uploader = None
    enable_upload = args.upload and not args.no_upload
    
    if enable_upload:
        try:
            logging.info("Initializing Google Drive uploader...")
            uploader = create_uploader(credentials_file=args.credentials)
            logging.info("✓ Google Drive uploader initialized")
        except Exception as e:
            logging.error(f"Failed to initialize Google Drive uploader: {e}")
            print(f"✗ Google Drive upload disabled due to: {e}")
            enable_upload = False
    
    try:
        # Process single image or all images
        if args.single:
            image_path = Path(args.single)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            result = process_single_image(
                image_path,
                output_dir,
                results_file,
                uploader=uploader,
                enable_upload=enable_upload,
                debug=args.debug
            )
            
            if result:
                print("✓ Image processing complete")
            else:
                print("✗ Image processing failed")
                sys.exit(1)
        else:
            # Process all images in directory
            results = process_all_images(
                input_dir,
                output_dir,
                results_file,
                uploader=uploader,
                enable_upload=enable_upload,
                debug=args.debug
            )
            
            print_summary(results)
    
    except Exception as e:
        logging.exception(f"Fatal error: {str(e)}")
        print(f"✗ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
