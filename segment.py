#!/usr/bin/env python3
import argparse
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from gdrive_uploader import GoogleDriveUploader

DEFAULT_INPUT_DIR = Path("duckweed_images")
DEFAULT_OUTPUT_DIR = Path("segmented_images")
DEFAULT_RESULTS_FILE = Path("results.csv")
LOG_FILE = Path("segment.log")


def setup_logging():
    """Configure logging to stdout and to a log file."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        ],
    )


def get_image_paths(image_dir: Path):
    """Return all supported image files in the input directory."""
    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory does not exist: {image_dir}")

    image_paths = [
        p for p in image_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]
    if not image_paths:
        raise FileNotFoundError(f"No images found in {image_dir}")

    return image_paths


def find_latest_image(image_dir: Path):
    """Return the newest image file based on modification time."""
    image_paths = get_image_paths(image_dir)
    latest = max(image_paths, key=lambda p: p.stat().st_mtime)
    return latest


def load_image(image_path: Path):
    """Load an image from disk using OpenCV."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise IOError(f"Could not read image: {image_path}")
    return image


def create_duckweed_mask(image):
    """Create a mask for green duckweed using HSV thresholds."""
    blurred = cv2.GaussianBlur(image, (7, 7), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    lower_green = np.array([30, 40, 40], dtype=np.uint8)
    upper_green = np.array([90, 255, 220], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # Remove bright reflections and very low-saturation pixels from the mask.
    value = hsv[:, :, 2]
    saturation = hsv[:, :, 1]
    reflection_mask = (value > 220) | (saturation < 40)
    mask[reflection_mask] = 0

    return mask


def refine_mask(mask):
    """Clean up the raw mask with morphology and remove small noisy regions."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    refined_mask = np.zeros_like(mask)
    minimum_area = 300
    for contour in contours:
        if cv2.contourArea(contour) >= minimum_area:
            cv2.drawContours(refined_mask, [contour], -1, 255, thickness=cv2.FILLED)

    return refined_mask


def calculate_coverage(mask) -> float:
    """Return the percentage of pixels identified as duckweed."""
    total_pixels = mask.size
    if total_pixels == 0:
        return 0.0

    duckweed_pixels = int(np.count_nonzero(mask))
    return round((duckweed_pixels / total_pixels) * 100.0, 2)


def build_overlay(image, mask):
    """Overlay detected duckweed on top of the original image for visualization."""
    overlay = image.copy()
    overlay[mask > 0] = (0, 255, 0)
    highlighted = cv2.addWeighted(image, 0.7, overlay, 0.3, 0)

    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(highlighted, contours, -1, (0, 0, 255), 2)

    return highlighted


def save_segmented_image(output_dir: Path, original_path: Path, segmented_image):
    """Save the overlay image to the segmented output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{original_path.stem}_segmented.png"
    success = cv2.imwrite(str(output_path), segmented_image)
    if not success:
        raise IOError(f"Failed to write segmented image to {output_path}")
    return output_path


def append_result(results_file: Path, image_path: Path, coverage: float, timestamp: str):
    """Write the coverage result row into the CSV results file."""
    header = ["image_filename", "timestamp", "tub_a_duckweed", "tub_a_water", "tub_b_duckweed", "tub_b_water"]
    file_exists = results_file.exists()
    with results_file.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists or results_file.stat().st_size == 0:
            writer.writerow(header)
        writer.writerow([image_path.name, timestamp, coverage])


def process_image(image_path: Path, output_dir: Path, results_file: Path):

    logging.info("Processing %s", image_path.name)

    image = load_image(image_path)

    raw_mask = create_duckweed_mask(image)

    mask = refine_mask(raw_mask)

    # ==========================
    # Tub Coordinates
    # ==========================
    left_tub_coords = (742, 611, 528)
    right_tub_coords = (1846, 638, 516)

    height, width = mask.shape

    mask_tub1 = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    mask_tub2 = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    cv2.circle(
        mask_tub1,
        (742, 611),
        528,
        255,
        -1
    )

    cv2.circle(
        mask_tub2,
        (1846, 638),
        516,
        255,
        -1
    )

    duckweed_tub1 = cv2.bitwise_and(
        mask,
        mask_tub1
    )

    duckweed_tub2 = cv2.bitwise_and(
        mask,
        mask_tub2
    )

    total_pixels_t1 = cv2.countNonZero(
        mask_tub1
    )

    total_pixels_t2 = cv2.countNonZero(
        mask_tub2
    )

    duckweed_pixels_t1 = cv2.countNonZero(
        duckweed_tub1
    )

    duckweed_pixels_t2 = cv2.countNonZero(
        duckweed_tub2
    )

    coverage_t1 = round(
        (
            duckweed_pixels_t1 /
            total_pixels_t1
        ) * 100,
        2
    )

    coverage_t2 = round(
        (
            duckweed_pixels_t2 /
            total_pixels_t2
        ) * 100,
        2
    )

    timestamp = datetime.fromtimestamp(
        image_path.stat().st_mtime
    ).isoformat(sep=" ")

    segmented_image = build_overlay(
        image,
        mask
    )

    output_path = save_segmented_image(
        output_dir,
        image_path,
        segmented_image
    )

    # Keep existing CSV working for now
    average_coverage = round(
        (
            coverage_t1 +
            coverage_t2
        ) / 2,
        2
    )

    append_result(
        results_file,
        image_path,
        average_coverage,
        timestamp
    )

    logging.info(
        "Tub A Coverage: %0.2f%%",
        coverage_t1
    )

    logging.info(
        "Tub B Coverage: %0.2f%%",
        coverage_t2
    )

    print(
        f"{image_path.name}"
    )

    print(
        f"Tub A: {coverage_t1:.2f}%"
    )

    print(
        f"Tub B: {coverage_t2:.2f}%"
    )

    return average_coverage, output_path


def parse_args():
    """Parse command-line arguments for input/output paths."""
    parser = argparse.ArgumentParser(
        description="Segment duckweed in the newest image from a folder or a specific image file."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directory containing duckweed input images.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for segmented output images.",
    )
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_RESULTS_FILE),
        help="CSV file path to store coverage results.",
    )
    parser.add_argument(
        "--image",
        help="Optional path to a specific image file to analyze instead of the newest file.",
    )
    return parser.parse_args()


def main():
    setup_logging()
    args = parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    results_file = Path(args.csv)

    try:
        if args.image:
            image_path = Path(args.image)
            if not image_path.exists():
                raise FileNotFoundError(f"Specified image does not exist: {image_path}")
        else:
            image_path = find_latest_image(input_dir)

        logging.info("Analyzing image: %s", image_path)
        coverage, output_path = process_image(image_path, output_dir, results_file)
        logging.info("Finished processing %s", image_path.name)
        
        # Automatically upload to Google Drive
        try:
            credentials_file = Path("credentials.json")
            if credentials_file.exists():
                uploader = GoogleDriveUploader(credentials_file=str(credentials_file))
            else:
                # Try to use cached credentials from token.pickle
                uploader = GoogleDriveUploader()
            
            uploader.upload_file(output_path)
            logging.info("Successfully uploaded segmented image to Google Drive")
        except Exception as upload_error:
            logging.warning(f"Could not upload to Google Drive: {upload_error}")
            logging.info("To enable automatic uploads, ensure Google Drive credentials are set up")
    except Exception as exc:
        logging.exception("Failed to analyze images: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
