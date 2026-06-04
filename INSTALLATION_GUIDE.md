# Installation & Quick Start Guide

## Quick Installation (5 minutes)

### 1. Install Python 3.7+ (if needed)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip

# macOS
brew install python3

# Verify installation
python3 --version
```

### 2. Install Dependencies

```bash
# Navigate to project directory
cd /path/to/duckweed-monitoring

# Install all required packages
pip3 install --break-system-packages -r requirements.txt
```

Or run the automated setup script:

```bash
chmod +x setup.sh
./setup.sh
```

### 3. Verify Installation

```bash
# Run test suite
python3 test_system.py
```

Expected output: All tests should pass ✓

## Quick Start (2 minutes)

### Basic Usage

```bash
# Process all images in duckweed_images/
python3 advanced_segment.py

# View results
ls segmented_images/
cat results.csv
```

### Quick Demo

```bash
# Process first available image with detailed output
python3 demo.py
```

### Single Image Processing

```bash
# Process specific image
python3 advanced_segment.py --single /path/to/image.jpg
```

## Google Drive Integration (Optional)

### Setup OAuth 2.0 Credentials

1. **Go to Google Cloud Console**
   - https://console.cloud.google.com/
   - Create a new project (e.g., "duckweed-monitoring")

2. **Enable Google Drive API**
   - API & Services → Library
   - Search for "Google Drive API"
   - Click "Enable"

3. **Create OAuth 2.0 Credentials**
   - API & Services → Credentials
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Select "Desktop application"
   - Download the JSON file as `credentials.json`

4. **Move credentials file**
   ```bash
   mv ~/Downloads/credentials.json /path/to/duckweed-monitoring/
   ```

5. **Enable upload in segmentation**
   ```bash
   python3 advanced_segment.py --upload --credentials credentials.json
   ```

### Setup Service Account (For Automated Systems)

1. **Create Service Account in Google Cloud Console**
   - API & Services → Credentials
   - "Create Credentials" → "Service Account"
   - Fill in service account name
   - Create and download JSON key file

2. **Set environment variable**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

3. **Enable upload**
   ```bash
   python3 advanced_segment.py --upload
   ```

## Troubleshooting

### Python ImportError

```bash
# Error: No module named 'google'
# Solution:
pip3 install --break-system-packages google-auth-oauthlib google-api-python-client

# Or with apt (Debian/Ubuntu):
sudo apt-get install python3-google-auth python3-google-api-client
```

### Permission Denied on setup.sh

```bash
# Make setup script executable
chmod +x setup.sh
```

### No module named 'cv2'

```bash
# Install opencv-python
pip3 install --break-system-packages opencv-python
```

### Google Drive Upload Fails

```bash
# Check credentials file exists and is valid
ls -la credentials.json

# Test authentication
python3 -c "from gdrive_uploader import create_uploader; uploader = create_uploader(credentials_file='credentials.json'); print('✓ Auth successful')"
```

## Full Command Reference

### Process All Images

```bash
python3 advanced_segment.py [options]
```

**Options:**
- `--input-dir PATH` - Input image directory (default: duckweed_images)
- `--output-dir PATH` - Output directory (default: segmented_images)
- `--csv PATH` - Results CSV file (default: results.csv)
- `--upload` - Enable Google Drive upload
- `--credentials PATH` - Path to Google credentials file
- `--debug` - Save intermediate processing images
- `--no-upload` - Disable upload even if credentials available

**Examples:**

```bash
# Basic processing
python3 advanced_segment.py

# With debug mode
python3 advanced_segment.py --debug

# With Google Drive upload
python3 advanced_segment.py --upload --credentials credentials.json

# Custom directories
python3 advanced_segment.py --input-dir /data/images --output-dir /data/results
```

### Process Single Image

```bash
python3 advanced_segment.py --single /path/to/image.jpg

# With upload
python3 advanced_segment.py --single /path/to/image.jpg --upload --credentials credentials.json
```

### Run Tests

```bash
# Full test suite
python3 test_system.py

# Quick demo
python3 demo.py
```

## Understanding Output

### Output Directory Structure

```
segmented_images/
├── water_masks/
│   └── image_name_water_mask.png      # Binary water region mask
├── duckweed_masks/
│   └── image_name_duckweed_mask.png   # Binary duckweed detection mask
├── contours/
│   └── image_name_contours.png         # Contour visualization
└── annotated/
    └── image_name_segmented.png        # Final result with coverage %
```

### Results CSV Format

```
timestamp,image_filename,container_type,water_area_pixels,duckweed_pixels,duckweed_coverage_percent,gdrive_upload_status
2026-05-28T12:34:56.123456,photo.jpg,circle,125000,48750,39.0,success
```

### Logs

- `segmentation.log` - Detailed processing logs
- Terminal output - Summary statistics and progress

## System Requirements

### Minimum

- Python 3.7+
- 256 MB RAM
- 100 MB disk space

### Recommended

- Python 3.9+
- 512 MB RAM (1 GB for batch processing)
- SSD for faster I/O

### For Raspberry Pi

- Raspberry Pi 3B+ or later
- Raspberry Pi OS (Bullseye or later)
- 1 GB RAM minimum

```bash
# Raspberry Pi setup
sudo apt-get update
sudo apt-get install python3-opencv python3-numpy python3-pil
pip3 install --break-system-packages google-auth-oauthlib google-api-python-client
```

## Advanced Configuration

### Adjust HSV Color Thresholds

Edit `duckweed_segmentation.py` line ~50:

```python
# For lighter green (adjust these values)
lower_green = np.array([25, 40, 30], dtype=np.uint8)
upper_green = np.array([95, 255, 220], dtype=np.uint8)
```

### Adjust Morphological Operations

Edit `duckweed_segmentation.py` line ~90:

```python
# Smaller kernel = less filtering
kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))  # Change from (5,5)
```

### Adjust Minimum Contour Area

Edit `duckweed_segmentation.py` line ~110:

```python
# Smaller value = keep more small regions
min_contour_area = int(image_area * 0.00005)  # Change from 0.0001
```

## Performance Optimization

### For Real-Time Processing

```bash
# Process with minimal debug output
python3 advanced_segment.py --no-upload
```

### For Batch Processing

```bash
# Process multiple images with statistics
for img in duckweed_images/*.jpg; do
  python3 advanced_segment.py --single "$img"
done

# View summary
tail -20 results.csv
```

### For Limited Resources (Raspberry Pi)

1. Reduce image resolution before processing
2. Disable debug mode: Don't use `--debug` flag
3. Disable uploads for faster processing: Use `--no-upload`

## Integration Examples

### Cron Job (Automated Hourly Captures)

```bash
# Add to crontab (crontab -e)
0 * * * * cd /home/pi/duckweed-monitoring && python3 advanced_segment.py --upload
```

### Python Script Integration

```python
from advanced_segment import process_single_image
from pathlib import Path

# Process image
result = process_single_image(
    Path("duckweed_images/photo.jpg"),
    Path("segmented_images"),
    Path("results.csv")
)

if result:
    print(f"Coverage: {result['coverage']:.2f}%")
```

### Bash Script Integration

```bash
#!/bin/bash
# run_segmentation.sh

IMAGE_DIR="duckweed_images"
RESULTS_CSV="results.csv"

for image in "$IMAGE_DIR"/*.jpg; do
    python3 advanced_segment.py --single "$image" --upload
    if [ $? -eq 0 ]; then
        echo "✓ Processed: $(basename $image)"
    else
        echo "✗ Failed: $(basename $image)"
    fi
done

# Print summary
echo ""
echo "Processing complete. Results:"
tail -5 "$RESULTS_CSV"
```

## Getting Help

### Check Logs

```bash
# View recent log entries
tail -50 segmentation.log

# View specific error
grep "ERROR" segmentation.log
```

### Run Diagnostics

```bash
# Test water detection on specific image
python3 -c "
import cv2
from water_detection import detect_water_container
img = cv2.imread('duckweed_images/test.jpg')
result = detect_water_container(img)
print(f'Container type: {result[\"container_type\"]}')
print(f'Water area: {result[\"area\"]} pixels')
"
```

### Enable Debug Mode

```bash
# Save all intermediate processing images
python3 advanced_segment.py --debug

# View intermediate images
ls -lh segmented_images/
```

## Next Steps

1. ✅ Install system and verify with `python3 test_system.py`
2. ✅ Process sample images: `python3 demo.py`
3. ✅ Setup Google Drive (optional): Follow "Google Drive Integration" section
4. ✅ Configure automated processing (optional): Use cron jobs or scheduling
5. ✅ Monitor results: Check `results.csv` and visualize trends

## Support & Documentation

- **README**: [SEGMENTATION_README.md](SEGMENTATION_README.md)
- **Code Documentation**: Inline comments in Python files
- **Logs**: Check `segmentation.log` for detailed error messages
- **Tests**: Run `python3 test_system.py` to verify installation

## License

This project is provided as-is for research and duckweed monitoring purposes.
