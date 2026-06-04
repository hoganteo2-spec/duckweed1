# High-Accuracy Duckweed Segmentation System

A complete Python-based duckweed monitoring system using OpenCV with:
- **Water container detection** (circular, oval, or polygon containers)
- **Green duckweed segmentation** using HSV color space
- **Advanced filtering** (morphological operations, contour filtering, noise removal)
- **Coverage calculation** (duckweed pixels / water pixels × 100)
- **Automatic Google Drive upload** for segmented images
- **Comprehensive output** (water masks, duckweed masks, contour images, annotated images)

## Features

✓ **High Accuracy**
- HSV-based green color detection with reflection/shadow removal
- Advanced morphological filtering for noise reduction
- Contour-based filtering to remove artifacts
- Edge-based water container detection supporting circular and oval containers

✓ **Robust Processing**
- Handles shadows, reflections, and varying lighting
- Supports sparse and dense duckweed coverage
- Automatic output folder creation
- Batch processing of multiple images

✓ **Integration**
- Automatic upload to Google Drive
- CSV logging of all results
- Comprehensive logging to file and terminal
- Debug mode with intermediate image outputs

✓ **Output Files**
- **water_mask.png** - Binary water region mask
- **duckweed_mask.png** - Binary duckweed detection mask
- **contours.png** - Contour visualization image
- **segmented.png** - Final annotated image with coverage %
- **results.csv** - Timestamp, coverage %, water area, upload status

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Quick Setup

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup script to install all dependencies
./setup.sh
```

### Manual Installation

```bash
# Upgrade pip
pip3 install --upgrade pip setuptools wheel

# Install dependencies
pip3 install -r requirements.txt
```

## Dependencies

```
opencv-python>=4.5.0          # Image processing
numpy>=1.20.0                  # Numerical computing
google-auth-oauthlib>=0.7.0   # Google Drive OAuth
google-auth-httplib2>=0.1.0   # Google Drive authentication
google-api-python-client>=2.50.0  # Google Drive API
google-auth>=2.0.0             # Authentication library
```

## Usage

### Basic Usage - Process All Images

```bash
python3 advanced_segment.py
```

Processes all images in `duckweed_images/` directory and saves results to `segmented_images/`.

### Process Single Image

```bash
python3 advanced_segment.py --single path/to/image.jpg
```

### Enable Google Drive Upload

First, set up Google credentials:

#### Option 1: OAuth 2.0 (Recommended for personal use)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google Drive API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials file as `credentials.json`
6. Run:

```bash
python3 advanced_segment.py --upload --credentials credentials.json
```

#### Option 2: Service Account (For automated systems)

1. Create a Service Account in Google Cloud Console
2. Download the JSON key file
3. Set environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

4. Run:

```bash
python3 advanced_segment.py --upload
```

### Enable Debug Mode

```bash
python3 advanced_segment.py --debug
```

Saves intermediate processing images in `segmented_images/` directory:
- HSV green mask
- After reflection removal
- After morphological operations
- After contour filtering

### Command-Line Options

```
--input-dir PATH           Input directory with images (default: duckweed_images)
--output-dir PATH          Output directory (default: segmented_images)
--csv PATH                 Results CSV file (default: results.csv)
--single PATH              Process single image by path
--upload                   Enable Google Drive upload
--credentials PATH         Path to Google credentials file
--debug                    Enable debug mode
--no-upload                Disable Google Drive upload
```

## Output Structure

```
segmented_images/
├── water_masks/
│   ├── image1_water_mask.png
│   └── image2_water_mask.png
├── duckweed_masks/
│   ├── image1_duckweed_mask.png
│   └── image2_duckweed_mask.png
├── contours/
│   ├── image1_contours.png
│   └── image2_contours.png
└── annotated/
    ├── image1_segmented.png
    └── image2_segmented.png

results.csv
segmentation.log
```

## Results CSV Format

| timestamp | image_filename | container_type | water_area_pixels | duckweed_pixels | duckweed_coverage_percent | gdrive_upload_status |
|-----------|----------------|----------------|-------------------|-----------------|---------------------------|----------------------|
| 2026-05-28T12:34:56.123456 | photo.jpg | circle | 125000 | 48750 | 39.0 | success |
| 2026-05-28T12:35:12.456789 | photo2.jpg | ellipse | 150000 | 67500 | 45.0 | success |

## Algorithm Details

### 1. Water Container Detection

Uses edge-based contour detection with support for:

- **Circular containers**: Hough Circle Detection
- **Oval containers**: Ellipse fitting
- **Polygon containers**: Contour-based detection

```python
# Automatic detection
water_result = water_detection.detect_water_container(image)
water_mask = water_result['water_mask']
container_type = water_result['container_type']  # circle, ellipse, or polygon
```

### 2. Duckweed Segmentation

HSV-based green color detection with advanced filtering:

```
Step 1: Convert to HSV color space
Step 2: Apply green color threshold (H:25-95, S:40-255, V:30-220)
Step 3: Remove bright reflections (V > 220 or S < 40)
Step 4: Remove dark shadows (V < 30)
Step 5: Morphological opening (remove small noise)
Step 6: Morphological closing (fill holes)
Step 7: Contour filtering (remove tiny artifacts)
Step 8: Clip to water region
```

### 3. Coverage Calculation

```
Coverage % = (Duckweed Pixels in Water / Total Water Pixels) × 100
```

Only duckweed pixels within the detected water region are counted.

## Example Output

```
================================================================================
Processing: photo_2026-05-28_12-40-01.jpg
================================================================================
Image size: 1920x1440
Step 1: Detecting water container...
  Container type: circle
  Water area: 156240 pixels
  Water area (refined): 155000 pixels
Step 2: Detecting duckweed...
Step 3: Calculating coverage...
  Coverage: 38.71%
  Duckweed pixels: 59987
Step 4: Building output images...
Step 5: Saving output files...
Step 6: Logging results...
Step 7: Uploading to Google Drive...
✓ Uploaded to Google Drive: photo_2026-05-28_12-40-01_segmented.png
  Link: https://drive.google.com/file/d/...

================================================================================
✓ Processing complete: photo_2026-05-28_12-40-01.jpg
  Container: circle
  Water area: 155000 pixels
  Duckweed: 59987 pixels
  Coverage: 38.71%
  Upload: success
  Output files:
    - segmented_images/water_masks/photo_2026-05-28_12-40-01_water_mask.png
    - segmented_images/duckweed_masks/photo_2026-05-28_12-40-01_duckweed_mask.png
    - segmented_images/contours/photo_2026-05-28_12-40-01_contours.png
    - segmented_images/annotated/photo_2026-05-28_12-40-01_segmented.png
================================================================================
```

## Troubleshooting

### No Water Container Detected

If the system fails to detect the water container:
- Ensure the container is clearly visible in the image
- Check lighting conditions (avoid extreme shadows)
- Verify image size is reasonable (not too small)
- Enable debug mode to see intermediate detection images

**Solution**: The system falls back to using the full image as the water region.

### Poor Duckweed Detection

If duckweed detection is inaccurate:
- Check lighting and reflection conditions
- Verify the duckweed is actually green (not brown/dead)
- Enable debug mode to inspect HSV ranges
- Adjust HSV thresholds in `duckweed_segmentation.py` if needed

### Google Drive Upload Failed

If upload fails:
- Verify credentials file is valid
- Check network connectivity
- Ensure Google Drive API is enabled in Cloud Console
- For OAuth: Credentials file expires after ~6 months; re-authenticate if needed
- Check logs: `segmentation.log`

### ImportError for Google Libraries

```bash
# Install specific version of google libraries
pip3 install --upgrade google-auth-oauthlib google-api-python-client
```

## Customization

### Adjust HSV Color Thresholds

Edit `duckweed_segmentation.py`, function `create_duckweed_mask()`:

```python
# Define HSV ranges for green duckweed
lower_green = np.array([25, 40, 30], dtype=np.uint8)
upper_green = np.array([95, 255, 220], dtype=np.uint8)
```

### Adjust Morphological Operations

Edit `duckweed_segmentation.py`, function `create_duckweed_mask()`:

```python
# Adjust kernel sizes and iteration counts
kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
```

### Adjust Minimum Contour Area

Edit `duckweed_segmentation.py`:

```python
min_contour_area = int(image_area * 0.0001)  # Change 0.0001 to filter more/less
```

## Performance

Typical processing time per image (on modern CPU):
- **Water detection**: 50-100ms
- **Duckweed segmentation**: 100-200ms
- **Image I/O and upload**: 200-1000ms
- **Total per image**: 350-1300ms

Google Drive upload time depends on file size and network speed.

## System Integration

### Raspberry Pi

The system is optimized for Raspberry Pi deployment:

```bash
# On Raspberry Pi (Raspberry Pi OS with Python 3.9+)
sudo apt-get update
sudo apt-get install python3-pip python3-opencv

# Run setup
chmod +x setup.sh
./setup.sh
```

### Cron Job (Automated Captures)

```bash
# Run segmentation every hour
0 * * * * cd /home/pi/duckweed-monitoring && python3 advanced_segment.py --upload

# Run segmentation every 30 minutes
*/30 * * * * cd /home/pi/duckweed-monitoring && python3 advanced_segment.py --upload
```

### Integration with capture.py

```python
# In capture.py, after image capture:
from advanced_segment import process_single_image

result = process_single_image(
    image_path,
    output_dir=Path("segmented_images"),
    results_file=Path("results.csv"),
    enable_upload=True
)

if result:
    print(f"✓ Coverage: {result['coverage']:.2f}%")
```

## Module Documentation

### water_detection.py

```python
from water_detection import detect_water_container, refine_water_mask

# Detect water container
result = detect_water_container(image, debug=False)
water_mask = result['water_mask']
container_type = result['container_type']  # circle, ellipse, polygon
area = result['area']

# Refine water mask
refined_mask = refine_water_mask(water_mask, image)
```

### duckweed_segmentation.py

```python
from duckweed_segmentation import (
    create_duckweed_mask,
    calculate_coverage,
    build_segmented_image,
    save_masks
)

# Create duckweed mask
result = create_duckweed_mask(image, water_mask, debug=False)
duckweed_mask = result['final_mask']

# Calculate coverage
coverage, duckweed_px, water_px = calculate_coverage(duckweed_mask, water_mask)

# Build output image
segmented_img = build_segmented_image(image, duckweed_mask, water_mask, coverage)

# Save all outputs
paths = save_masks(output_dir, image_name, water_mask, duckweed_mask, 
                   segmented_img, contour_img)
```

### gdrive_uploader.py

```python
from gdrive_uploader import create_uploader

# Initialize uploader
uploader = create_uploader(credentials_file="credentials.json")

# Upload single file
result = uploader.upload_file(Path("segmented_images/photo_segmented.png"))

# Upload multiple files
files = [Path("file1.png"), Path("file2.png")]
results = uploader.upload_multiple(files, subfolder="batch_2026_05_28")
```

## License

This project is provided as-is for research and monitoring purposes.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Enable debug mode and inspect intermediate images
3. Review logs in `segmentation.log`
4. Ensure all dependencies are correctly installed

## Future Enhancements

- [ ] Dashboard visualization with trend charts
- [ ] Web interface for real-time monitoring
- [ ] Deep learning-based segmentation (semantic segmentation)
- [ ] Mobile app for status monitoring
- [ ] Email/SMS alerts on coverage thresholds
- [ ] Historical analysis and trend reporting
- [ ] Multi-container support
- [ ] Custom ROI (Region of Interest) definition
