# Raspberry Pi Duckweed Monitoring System

A lightweight Raspberry Pi prototype for capturing images, segmenting duckweed with OpenCV, and storing coverage results for long-term analysis.

## Project Structure

- `capture.py` - capture a camera image and save it to `duckweed_images/`
- `segment.py` - analyze the latest image, segment green duckweed, and save results
- `duckweed_images/` - raw captured photos
- `segmented_images/` - segmented output images with duckweed overlay
- `results.csv` - time-series data for dashboarding
- `requirements.txt` - Python package dependencies

## Required Python Libraries

Recommended install method on Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y python3-pip python3-opencv
python3 -m pip install --user -r requirements.txt
```

If `python3-opencv` is installed via apt, the pip install step is still useful for `numpy`.

## Google Drive Upload with rclone

This project now uploads every captured image to Google Drive automatically using `rclone`.

### Install rclone on Raspberry Pi

```bash
sudo apt update
sudo apt install -y curl unzip
curl https://rclone.org/install.sh | sudo bash
```

If you prefer the Debian package, you can also use:

```bash
sudo apt install -y rclone
```

### Configure Google Drive authentication

Run the interactive setup and choose `drive` as the storage type:

```bash
rclone config
```

Follow the prompts:

1. `n` to create a new remote
2. Name it `gdrive`
3. Choose `drive` for Google Drive
4. Accept defaults for `client_id` and `client_secret`
5. Use `auto config` if you have a browser available; otherwise choose `n` and follow the manual steps
6. Grant access to your Google account when prompted
7. Finish configuration and confirm the remote works with `rclone listremotes`

### Google Drive folder setup

- Create a Google Drive folder called `duckweed_images` or let `rclone` create it automatically.
- The Python script uploads to `gdrive:duckweed_images` by default.
- If you want a different Drive folder, adjust the `--upload-folder` option when calling `capture.py`.

## How to Use

Capture a new image and upload to Google Drive:

```bash
python3 capture.py
```

Capture only without upload (for local testing):

```bash
python3 capture.py --skip-upload
```

Analyze the latest captured image:

```bash
python3 segment.py
```

Analyze a specific image:

```bash
python3 segment.py --image duckweed_images/2026-05-20_12-00-00.jpg
```

## Testing the Segmentation

1. Capture an image with `python3 capture.py`.
2. Run `python3 segment.py`.
3. Check `results.csv` for a new row with `duckweed_percent`.
4. Open the corresponding `segmented_images/*_segmented.png` file to verify the green overlay.

## Automating with Cron Jobs

The pipeline can be automated with cron by running capture first, then segmentation.

Open the cron editor:

```bash
crontab -e
```

Add entries like this:

```cron
0 0,6,12,18 * * * /usr/bin/python3 /home/pi/capture.py >> /home/pi/capture.log 2>&1
5 0,6,12,18 * * * /usr/bin/python3 /home/pi/segment.py >> /home/pi/segment.log 2>&1
@reboot /usr/bin/python3 /home/pi/capture.py >> /home/pi/capture.log 2>&1
```

Adjust `/home/pi/` to your actual home path.

### Testing uploads manually before automation

1. Verify `rclone` is installed and the remote is configured:

```bash
rclone listremotes
rclone lsd gdrive:
```

2. Capture a local image without upload:

```bash
python3 capture.py --skip-upload
```

3. Upload a single image manually:

```bash
rclone copy duckweed_images/<filename>.jpg gdrive:duckweed_images
```

4. Capture and upload automatically:

```bash
python3 capture.py
```

5. Confirm the file exists in Google Drive:

```bash
rclone lsf gdrive:duckweed_images
```

If the upload works manually, the cron automation will also work after reboot.

## Recommended Camera Positioning

- Mount the Raspberry Pi Camera directly above the pond surface, pointing downward.
- Keep the camera level and centered over the growth area.
- Use a fixed mount to avoid movement between captures.
- Leave a small margin around the water so the full surface is visible.

## Recommended Lighting Conditions

- Use consistent daylight or a dedicated LED light source.
- Avoid strong shadows, reflections, or glare on the water.
- If possible, use diffuse lighting or a small light box.
- Capture at the same time each day for stable results.

## Notes for Power BI Integration

- `results.csv` is structured for easy import into Power BI.
- Each row contains `image_filename`, `timestamp`, and `duckweed_percent`.
- Keep the file in a shared location or cloud folder for dashboard refresh.
