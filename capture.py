#!/usr/bin/env python3
import argparse
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import segment

IMAGE_DIR = Path("duckweed_images")
SEGMENTED_DIR = Path("segmented_images")
RESULTS_FILE = Path("results.csv")
LOG_FILE = Path("capture.log")
DEFAULT_UPLOAD_REMOTE = "gdrive"
DEFAULT_UPLOAD_FOLDER = "duckweed_images"

SUPPORTED_CAMERA_COMMANDS = [
    ["rpicam-jpeg", "-o"],
    ["libcamera-jpeg", "-o"],
    ["raspistill", "-o"],
]


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        ],
    )


def ensure_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_camera_command():
    for command in SUPPORTED_CAMERA_COMMANDS:
        if shutil.which(command[0]):
            return command
    return None


def find_rclone_command():
    return shutil.which("rclone")


def upload_image(source: Path, remote: str, remote_folder: str):
    rclone = find_rclone_command()
    if not rclone:
        raise FileNotFoundError(
            "rclone is not installed. Install rclone and configure a Google Drive remote before uploading."
        )

    destination = f"{remote}:{remote_folder}/{source.name}"
    logging.info("Uploading image to Google Drive: %s", destination)
    result = subprocess.run(
        [rclone, "copyto", str(source), destination],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        logging.error("Upload failed: %s", stderr)
        raise RuntimeError(
            f"Upload failed for {source.name}. Check rclone configuration and network connectivity."
        )
    logging.info("Upload completed successfully")
    return destination


def capture_image(destination: Path, camera_command=None):
    ensure_directory(destination.parent)
    if camera_command:
        command = camera_command.split() + [str(destination)]
    else:
        selected = find_camera_command()
        if not selected:
            raise FileNotFoundError(
                "No supported camera command found. Install rpicam-jpeg, libcamera-jpeg, or raspistill."
            )
        command = selected + [str(destination)]

    logging.info("Capturing image to %s", destination)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error("Camera command failed: %s", result.stderr.strip())
        raise RuntimeError(f"Capture command failed with exit code {result.returncode}")
    logging.info("Capture completed successfully")
    return destination


def analyze_image(image_path: Path):
    """Run the segmentation analysis on a single captured image."""
    try:
        logging.info("Starting segmentation for %s", image_path)
        segment.process_image(image_path, SEGMENTED_DIR, RESULTS_FILE)
        logging.info("Segmentation finished for %s", image_path.name)
    except Exception:
        logging.exception("Segmentation failed for %s", image_path)
        raise


def parse_args():
    parser = argparse.ArgumentParser(
        description="Capture a Raspberry Pi camera image for duckweed monitoring and analyze it automatically."
    )
    parser.add_argument(
        "--output-dir",
        default=str(IMAGE_DIR),
        help="Directory to save captured images.",
    )
    parser.add_argument(
        "--camera-cmd",
        help="Custom camera command prefix, e.g. 'libcamera-jpeg -o'.",
    )
    parser.add_argument(
        "--upload-remote",
        default=DEFAULT_UPLOAD_REMOTE,
        help="rclone remote name configured for Google Drive.",
    )
    parser.add_argument(
        "--upload-folder",
        default=DEFAULT_UPLOAD_FOLDER,
        help="Folder path inside Google Drive remote to upload images.",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Capture only and skip the Google Drive upload step.",
    )
    return parser.parse_args()


def main():
    setup_logging()
    args = parse_args()

    image_dir = Path(args.output_dir)
    ensure_directory(image_dir)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destination = image_dir / f"{timestamp}.jpg"

    try:
        capture_image(destination, args.camera_cmd)
        print("Image captured:", destination)
        analyze_image(destination)
        if args.skip_upload:
            logging.info("Upload skipped by command-line option.")
            print("Upload skipped.")
        else:
            upload_destination = upload_image(destination, args.upload_remote, args.upload_folder)
            print("Image uploaded to Google Drive:", upload_destination)
    except Exception as exc:
        logging.exception("Capture or analysis failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
