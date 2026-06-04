#!/usr/bin/env python3
"""
Test Script - Verify Installation and Test Duckweed Segmentation System
"""

import sys
import logging
from pathlib import Path

def test_imports():
    """Test if all required packages are installed."""
    print("\n" + "="*80)
    print("TEST 1: Checking Python Imports")
    print("="*80)
    
    packages = [
        ('cv2', 'opencv-python'),
        ('numpy', 'numpy'),
        ('google.auth', 'google-auth'),
        ('google.oauth2', 'google-auth'),
        ('google_auth_oauthlib', 'google-auth-oauthlib'),
        ('googleapiclient', 'google-api-python-client'),
    ]
    
    failed = []
    for module, package in packages:
        try:
            __import__(module)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - NOT INSTALLED")
            failed.append(package)
    
    if failed:
        print(f"\n✗ {len(failed)} packages missing. Install with:")
        print(f"  pip3 install {' '.join(failed)}")
        return False
    else:
        print(f"\n✓ All packages imported successfully")
        return True


def test_modules():
    """Test if custom modules are available."""
    print("\n" + "="*80)
    print("TEST 2: Checking Custom Modules")
    print("="*80)
    
    modules = [
        'water_detection',
        'duckweed_segmentation',
        'gdrive_uploader',
        'advanced_segment'
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}.py")
        except ImportError as e:
            print(f"✗ {module}.py - {str(e)}")
            failed.append(module)
    
    if failed:
        print(f"\n✗ {len(failed)} modules not found")
        return False
    else:
        print(f"\n✓ All custom modules found")
        return True


def test_directories():
    """Test if required directories exist."""
    print("\n" + "="*80)
    print("TEST 3: Checking Directory Structure")
    print("="*80)
    
    directories = [
        Path('duckweed_images'),
    ]
    
    for directory in directories:
        if directory.exists():
            files = list(directory.glob('*'))
            images = [f for f in files if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}]
            if images:
                print(f"✓ {directory} ({len(images)} images found)")
            else:
                print(f"⚠ {directory} (empty - no images)")
        else:
            print(f"⚠ {directory} (does not exist - will be created)")
            directory.mkdir(parents=True, exist_ok=True)
    
    return True


def test_water_detection():
    """Test water detection module."""
    print("\n" + "="*80)
    print("TEST 4: Testing Water Detection")
    print("="*80)
    
    try:
        import cv2
        import numpy as np
        import water_detection
        
        # Create a test image with a circular container
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Draw background
        test_image[:] = (100, 150, 100)  # Greenish background
        
        # Draw circular water container
        cv2.circle(test_image, (320, 240), 150, (50, 100, 200), -1)  # Blue circle (water)
        
        # Add some noise
        noise = np.random.randint(0, 10, test_image.shape, dtype=np.uint8)
        test_image = cv2.add(test_image, noise)
        
        # Test detection
        result = water_detection.detect_water_container(test_image)
        
        print(f"✓ Water detection completed")
        print(f"  Container type: {result['container_type']}")
        print(f"  Water area: {result['area']} pixels")
        print(f"  Container center: {result['center']}")
        print(f"  Container radius: {result['radius']}")
        
        return True
    
    except Exception as e:
        print(f"✗ Water detection failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_duckweed_segmentation():
    """Test duckweed segmentation module."""
    print("\n" + "="*80)
    print("TEST 5: Testing Duckweed Segmentation")
    print("="*80)
    
    try:
        import cv2
        import numpy as np
        import duckweed_segmentation
        
        # Create test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Draw background
        test_image[:] = (100, 150, 100)
        
        # Draw water container (blue)
        cv2.circle(test_image, (320, 240), 150, (50, 100, 200), -1)
        
        # Draw duckweed patches (green)
        cv2.circle(test_image, (280, 200), 50, (100, 200, 100), -1)  # Bright green
        cv2.circle(test_image, (340, 260), 40, (80, 180, 80), -1)    # Darker green
        
        # Create water mask
        water_mask = np.zeros((480, 640), dtype=np.uint8)
        cv2.circle(water_mask, (320, 240), 150, 255, -1)
        
        # Test segmentation
        result = duckweed_segmentation.create_duckweed_mask(test_image, water_mask)
        duckweed_mask = result['final_mask']
        
        # Calculate coverage
        coverage, duckweed_px, water_px = duckweed_segmentation.calculate_coverage(
            duckweed_mask, water_mask
        )
        
        print(f"✓ Duckweed segmentation completed")
        print(f"  Water pixels: {water_px}")
        print(f"  Duckweed pixels: {duckweed_px}")
        print(f"  Coverage: {coverage:.2f}%")
        
        return True
    
    except Exception as e:
        print(f"✗ Duckweed segmentation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_output_creation():
    """Test output directory creation."""
    print("\n" + "="*80)
    print("TEST 6: Testing Output Directory Creation")
    print("="*80)
    
    try:
        import duckweed_segmentation
        import cv2
        import numpy as np
        
        output_dir = Path("test_output")
        
        # Create test images
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        water_mask = np.ones((480, 640), dtype=np.uint8) * 255
        duckweed_mask = np.random.randint(0, 2, (480, 640), dtype=np.uint8) * 255
        segmented_img = test_image.copy()
        contour_img = test_image.copy()
        
        # Save masks
        paths = duckweed_segmentation.save_masks(
            output_dir,
            "test_image.jpg",
            water_mask,
            duckweed_mask,
            segmented_img,
            contour_img
        )
        
        # Verify all files were created
        created_files = []
        for key, path in paths.items():
            if Path(path).exists():
                created_files.append(path.name)
                print(f"✓ Created: {path}")
            else:
                print(f"✗ Failed to create: {path}")
        
        # Clean up
        import shutil
        if output_dir.exists():
            shutil.rmtree(output_dir)
            print(f"✓ Cleaned up test output directory")
        
        if len(created_files) == 4:
            return True
        else:
            print(f"✗ Only {len(created_files)}/4 files created")
            return False
    
    except Exception as e:
        print(f"✗ Output creation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_real_image():
    """Test on real image if available."""
    print("\n" + "="*80)
    print("TEST 7: Testing on Real Image (if available)")
    print("="*80)
    
    image_dir = Path('duckweed_images')
    image_files = list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.png'))
    
    if not image_files:
        print("ℹ No test images found in duckweed_images/ - Skipping this test")
        return True
    
    try:
        import cv2
        import water_detection
        import duckweed_segmentation
        
        test_image_path = image_files[0]
        print(f"Testing with: {test_image_path.name}")
        
        image = cv2.imread(str(test_image_path))
        if image is None:
            print(f"✗ Failed to load image: {test_image_path}")
            return False
        
        # Test water detection
        water_result = water_detection.detect_water_container(image)
        water_mask = water_result['water_mask']
        print(f"✓ Water detected: {water_result['container_type']} ({water_result['area']} pixels)")
        
        # Test duckweed detection
        duckweed_result = duckweed_segmentation.create_duckweed_mask(image, water_mask)
        duckweed_mask = duckweed_result['final_mask']
        
        # Calculate coverage
        coverage, duckweed_px, water_px = duckweed_segmentation.calculate_coverage(
            duckweed_mask, water_mask
        )
        print(f"✓ Duckweed detected: {duckweed_px} pixels")
        print(f"✓ Coverage calculated: {coverage:.2f}%")
        
        return True
    
    except Exception as e:
        print(f"✗ Real image test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def print_summary(results):
    """Print test summary."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    total = len(results)
    passed = sum(1 for r in results if r)
    failed = total - passed
    
    for i, result in enumerate(results, 1):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"Test {i}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if failed == 0:
        print("\n✓ All tests passed! System is ready to use.")
        return True
    else:
        print(f"\n✗ {failed} test(s) failed. Please fix the issues above.")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("DUCKWEED SEGMENTATION SYSTEM - TEST SUITE")
    print("="*80)
    
    results = [
        test_imports(),
        test_modules(),
        test_directories(),
        test_water_detection(),
        test_duckweed_segmentation(),
        test_output_creation(),
        test_real_image(),
    ]
    
    success = print_summary(results)
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("""
To process images:

1. Place images in duckweed_images/ directory

2. Run the segmentation system:
   python3 advanced_segment.py

3. View results in:
   - segmented_images/ (output images)
   - results.csv (statistics)
   - segmentation.log (detailed log)

For more options:
   python3 advanced_segment.py --help

For Google Drive upload:
   python3 advanced_segment.py --upload --credentials credentials.json
    """)
    print("="*80 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
