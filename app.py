#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, abort, render_template, send_from_directory, url_for

app = Flask(__name__, static_folder="static", template_folder="templates")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
ORIGINAL_DIR = OUTPUT_DIR / "original"
FINAL_DIR = OUTPUT_DIR / "final"
SEGMENTED_DIR = OUTPUT_DIR / "segmented"
MASK_DIR = OUTPUT_DIR / "duckweed_masks"
COVERAGE_JSON = OUTPUT_DIR / "coverage.json"
COVERAGE_TXT = OUTPUT_DIR / "coverage.txt"
HISTORY_JSON = OUTPUT_DIR / "coverage_history.json"

ALLOWED_FOLDERS = {
    "original": ORIGINAL_DIR,
    "final": FINAL_DIR,
    "segmented": SEGMENTED_DIR,
    "duckweed_masks": MASK_DIR,
}

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def ensure_directories():
    for folder in ALLOWED_FOLDERS.values():
        folder.mkdir(parents=True, exist_ok=True)


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def latest_image(directory: Path) -> Optional[Path]:
    if not directory.exists():
        return None
    images = [p for p in directory.iterdir() if is_image_file(p)]
    if not images:
        return None
    return max(images, key=lambda p: p.stat().st_mtime)


def list_images(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    return sorted([p for p in directory.iterdir() if is_image_file(p)], key=lambda p: p.stat().st_mtime)


def format_timestamp(timestamp: Optional[datetime]) -> str:
    if not timestamp:
        return "No updates yet"
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def read_json_file(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_latest_coverage() -> Optional[Dict[str, str]]:
    if HISTORY_JSON.exists():
        history = read_coverage_history()
        if history:
            latest = history[-1]
            return {
                "coverage": latest.get("coverage"),
                "timestamp": latest.get("timestamp", format_timestamp(datetime.fromtimestamp(HISTORY_JSON.stat().st_mtime)))
            }

    if COVERAGE_JSON.exists():
        data = read_json_file(COVERAGE_JSON)
        if isinstance(data, dict) and data.get("coverage") is not None:
            return {
                "coverage": data["coverage"],
                "timestamp": data.get("timestamp", format_timestamp(datetime.fromtimestamp(COVERAGE_JSON.stat().st_mtime)))
            }

    if COVERAGE_TXT.exists():
        try:
            value = COVERAGE_TXT.read_text(encoding="utf-8").strip()
            coverage_value = float(value)
            return {
                "coverage": coverage_value,
                "timestamp": format_timestamp(datetime.fromtimestamp(COVERAGE_TXT.stat().st_mtime))
            }
        except Exception:
            return None

    return None


def read_coverage_history() -> List[Dict[str, str]]:
    if HISTORY_JSON.exists():
        data = read_json_file(HISTORY_JSON)
        if isinstance(data, list):
            return [entry for entry in data if isinstance(entry, dict) and entry.get("coverage") is not None]
        if isinstance(data, dict) and isinstance(data.get("history"), list):
            return [entry for entry in data["history"] if isinstance(entry, dict) and entry.get("coverage") is not None]
    return []


def latest_update_time() -> Optional[datetime]:
    latest = None
    for path in [ORIGINAL_DIR, FINAL_DIR, SEGMENTED_DIR, MASK_DIR]:
        image = latest_image(path)
        if image is not None:
            image_time = datetime.fromtimestamp(image.stat().st_mtime)
            if latest is None or image_time > latest:
                latest = image_time
    coverage = read_latest_coverage()
    if coverage and coverage.get("timestamp"):
        try:
            parsed = datetime.fromisoformat(str(coverage["timestamp"]))
            if latest is None or parsed > latest:
                latest = parsed
        except ValueError:
            pass
    return latest


def count_processed_images() -> int:
    return len(list_images(FINAL_DIR))


@app.route("/")
def index():
    ensure_directories()

    latest_original = latest_image(ORIGINAL_DIR)
    latest_final = latest_image(FINAL_DIR)
    latest_segmented = latest_image(SEGMENTED_DIR)
    latest_mask = latest_image(MASK_DIR)

    coverage_info = read_latest_coverage()
    history_data = read_coverage_history()

    latest_time = latest_update_time()
    status = "Running" if coverage_info or latest_final or latest_segmented or latest_mask else "Waiting for data"

    return render_template(
        "index.html",
        latest_original=latest_original,
        latest_final=latest_final,
        latest_segmented=latest_segmented,
        latest_mask=latest_mask,
        coverage_info=coverage_info,
        history_data=history_data,
        total_processed=count_processed_images(),
        latest_time=format_timestamp(latest_time),
        status=status,
    )


@app.route("/outputs/<folder>/<path:filename>")
def output_image(folder: str, filename: str):
    if folder not in ALLOWED_FOLDERS:
        abort(404)
    directory = ALLOWED_FOLDERS[folder]
    safe_filename = Path(filename).name
    return send_from_directory(directory, safe_filename)


if __name__ == "__main__":
    ensure_directories()
    app.run(host="0.0.0.0", port=5000, debug=True)
