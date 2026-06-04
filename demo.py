#!/usr/bin/env python3
"""
Quick Start Demo - Run segmentation on first available image
"""

import sys
from pathlib import Path
from advanced_segment import process_single_image

def main():
    # Find first image
    image_dir = Path('duckweed_images')
    images = list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.png'))
    
    if not images:
        print("✗ No images found in duckweed_images/")
        print("  Add some images first: cp path/to/image.jpg duckweed_images/")
        sys.exit(1)
    
    image_path = images[0]
    output_dir = Path('segmented_images')
    results_file = Path('results.csv')
    
    print("="*80)
    print("DUCKWEED SEGMENTATION - QUICK START DEMO")
    print("="*80)
    print(f"\nProcessing image: {image_path.name}")
    print(f"Output directory: {output_dir}")
    print(f"Results file: {results_file}\n")
    
    # Process image
    result = process_single_image(
        image_path,
        output_dir,
        results_file,
        uploader=None,
        enable_upload=False,
        debug=False
    )
    
    if result:
        print("\n" + "="*80)
        print("✓ SUCCESS!")
        print("="*80)
        print(f"\nCoverage: {result['coverage']:.2f}%")
        print(f"Water area: {result['water_area']} pixels")
        print(f"Duckweed area: {result['duckweed_pixels']} pixels")
        print(f"\nOutput files created in: {output_dir}/")
        print(f"Results logged in: {results_file}")
        print("\n" + "="*80)
        return 0
    else:
        print("\n✗ FAILED - See logs for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
