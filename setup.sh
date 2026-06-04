#!/bin/bash
# Installation and Setup Guide
# Run this script to install all dependencies

echo "========================================"
echo "Duckweed Segmentation System - Setup"
echo "========================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 is not installed. Please install Python 3.7+ first."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "✗ pip3 is not installed. Please install pip3 first."
    exit 1
fi

echo "✓ pip3 found"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install --upgrade pip setuptools wheel

echo "Installing requirements from requirements.txt..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ All dependencies installed successfully"
else
    echo "✗ Failed to install dependencies"
    exit 1
fi

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Prepare Google Drive credentials (optional for upload):"
echo "   - For OAuth 2.0: Download credentials.json from Google Cloud Console"
echo "   - For Service Account: Download JSON key file"
echo ""
echo "2. Create input image directory (if not exists):"
echo "   mkdir -p duckweed_images"
echo ""
echo "3. Run the segmentation system:"
echo ""
echo "   Process all images:"
echo "   python3 advanced_segment.py"
echo ""
echo "   Process single image:"
echo "   python3 advanced_segment.py --single path/to/image.jpg"
echo ""
echo "   Enable Google Drive upload:"
echo "   python3 advanced_segment.py --upload --credentials path/to/credentials.json"
echo ""
echo "   Enable debug mode (save intermediate images):"
echo "   python3 advanced_segment.py --debug"
echo ""
echo "4. Check results:"
echo "   - View results in: segmented_images/"
echo "   - View statistics in: results.csv"
echo "   - View logs in: segmentation.log"
echo ""
echo "========================================"
