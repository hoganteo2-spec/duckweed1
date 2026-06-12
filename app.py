import streamlit as st
import pandas as pd
import numpy as np
import os
import cv2
import time
from datetime import datetime
import threading

# --- Configuration ---
IMAGE_DIR = "duckweed_images"
OUTPUT_DIR = "segmented_duckweed"
LIVE_DIR = "live_feed"
DB_FILE = "growth_log.csv"

# Streamlit page
st.set_page_config(page_title="Duckweed Growth Monitor", layout="wide")
st.title("🌿 Real-Time Duckweed Cultivation Dashboard")
st.markdown("Automated image tracking, segmentation parsing, and local database logging.")

# Ensure folders exist
for folder in [IMAGE_DIR, OUTPUT_DIR, LIVE_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Processing lock
processing_lock = threading.Lock()


def process_and_log_images():
    acquired = processing_lock.acquire(blocking=False)
    if not acquired:
        return None
    try:
        if not os.path.exists(IMAGE_DIR):
            return None

        files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        if not files:
            return None

        files = sorted(files, key=lambda f: os.path.getmtime(os.path.join(IMAGE_DIR, f)))

        if os.path.exists(DB_FILE):
            log_df = pd.read_csv(DB_FILE)
        else:
            log_df = pd.DataFrame(columns=['Timestamp', 'Filename', 'Tub 1 Duckweed %', 'Tub 1 Water %', 'Tub 2 Duckweed %', 'Tub 2 Water %'])

        processed = set(log_df['Filename'].tolist()) if not log_df.empty else set()

        left_tub_coords = (742, 611, 528)
        right_tub_coords = (1846, 638, 516)
        LOWER_GREEN = np.array([25, 35, 35])
        UPPER_GREEN = np.array([90, 255, 255])
        kernel = np.ones((3, 3), np.uint8)

        new_rows = []

        for fname in files:
            img_path = os.path.join(IMAGE_DIR, fname)
            img = cv2.imread(img_path)
            if img is None:
                continue

            h, w, _ = img.shape
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            global_dw = cv2.inRange(hsv, LOWER_GREEN, UPPER_GREEN)
            global_dw = cv2.morphologyEx(global_dw, cv2.MORPH_OPEN, kernel)

            mask1 = np.zeros((h, w), dtype=np.uint8)
            cv2.circle(mask1, (left_tub_coords[0], left_tub_coords[1]), left_tub_coords[2], 255, -1)
            mask2 = np.zeros((h, w), dtype=np.uint8)
            cv2.circle(mask2, (right_tub_coords[0], right_tub_coords[1]), right_tub_coords[2], 255, -1)

            total1 = cv2.countNonZero(mask1)
            total2 = cv2.countNonZero(mask2)

            dw1 = cv2.bitwise_and(global_dw, mask1)
            dw2 = cv2.bitwise_and(global_dw, mask2)

            pct1 = (cv2.countNonZero(dw1) / total1 * 100) if total1 > 0 else 0.0
            pct2 = (cv2.countNonZero(dw2) / total2 * 100) if total2 > 0 else 0.0

            archive = img.copy()
            water_mask_archive = cv2.bitwise_and(cv2.bitwise_not(global_dw), cv2.bitwise_or(mask1, mask2))
            archive[global_dw > 0] = [0, 255, 0]
            archive[water_mask_archive > 0] = [255, 50, 50]
            background_mask = cv2.bitwise_not(cv2.bitwise_or(mask1, mask2)) > 0
            archive[background_mask] = tuple(c // 4 for c in img[background_mask])

            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.rectangle(archive, (15, 15), (360, 105), (0, 0, 0), -1)
            cv2.putText(archive, "TUB 1 (Left Mesocosm)", (25, 40), font, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(archive, f"Duckweed: {pct1:.2f}%", (25, 65), font, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(archive, f"Open Water: {100.0 - pct1:.2f}%", (25, 90), font, 0.55, (255, 200, 0), 2, cv2.LINE_AA)

            cv2.rectangle(archive, (w - 360, 15), (w - 15, 105), (0, 0, 0), -1)
            cv2.putText(archive, "TUB 2 (Right Mesocosm)", (w - 350, 40), font, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(archive, f"Duckweed: {pct2:.2f}%", (w - 350, 65), font, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(archive, f"Open Water: {100.0 - pct2:.2f}%", (w - 350, 90), font, 0.55, (255, 200, 0), 2, cv2.LINE_AA)

            out_path = os.path.join(OUTPUT_DIR, f"split_analysis_{fname}")
            cv2.imwrite(out_path, archive)

            if fname not in processed:
                ts = datetime.fromtimestamp(os.path.getmtime(img_path)).strftime('%Y-%m-%d %H:%M:%S')
                new_rows.append({
                    'Timestamp': ts,
                    'Filename': fname,
                    'Tub 1 Duckweed %': round(pct1, 2),
                    'Tub 1 Water %': round(100.0 - pct1, 2),
                    'Tub 2 Duckweed %': round(pct2, 2),
                    'Tub 2 Water %': round(100.0 - pct2, 2)
                })

        if new_rows:
            log_df = pd.concat([log_df, pd.DataFrame(new_rows)], ignore_index=True)
            log_df.to_csv(DB_FILE, index=False)

        latest = max(files, key=lambda f: os.path.getmtime(os.path.join(IMAGE_DIR, f)))
        latest_path = os.path.join(IMAGE_DIR, latest)
        img_latest = cv2.imread(latest_path)
        h, w, _ = img_latest.shape
        hsv_latest = cv2.cvtColor(img_latest, cv2.COLOR_BGR2HSV)
        global_dw_latest = cv2.inRange(hsv_latest, LOWER_GREEN, UPPER_GREEN)
        global_dw_latest = cv2.morphologyEx(global_dw_latest, cv2.MORPH_OPEN, kernel)

        mask1 = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask1, (left_tub_coords[0], left_tub_coords[1]), left_tub_coords[2], 255, -1)
        mask2 = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask2, (right_tub_coords[0], right_tub_coords[1]), right_tub_coords[2], 255, -1)

        dw_mask_t1 = cv2.bitwise_and(global_dw_latest, mask1)
        dw_mask_t2 = cv2.bitwise_and(global_dw_latest, mask2)
        water_mask_t1 = cv2.bitwise_and(cv2.bitwise_not(dw_mask_t1), mask1)
        water_mask_t2 = cv2.bitwise_and(cv2.bitwise_not(dw_mask_t2), mask2)

        output_img = img_latest.copy()
        output_img[cv2.bitwise_or(dw_mask_t1, dw_mask_t2) > 0] = [0, 255, 0]
        output_img[cv2.bitwise_or(water_mask_t1, water_mask_t2) > 0] = [255, 50, 50]
        output_img[cv2.bitwise_not(cv2.bitwise_or(mask1, mask2)) > 0] = tuple(c // 4 for c in img_latest[cv2.bitwise_not(cv2.bitwise_or(mask1, mask2)) > 0])

        temp_path = os.path.join(LIVE_DIR, "temp_live_stream_feed.jpg")
        final_path = os.path.join(LIVE_DIR, "live_stream_feed.jpg")
        cv2.imwrite(temp_path, output_img)
        try:
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.rename(temp_path, final_path)
        except Exception:
            pass

        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE)
            df['FileTime'] = df['Filename'].apply(lambda f: os.path.getmtime(os.path.join(IMAGE_DIR, f)) if os.path.exists(os.path.join(IMAGE_DIR, f)) else 0)
            df = df.sort_values(by='FileTime').drop(columns=['FileTime'])
            latest_entry = df.iloc[-1].to_dict() if not df.empty else None
            return latest_entry, df
        return None
    finally:
        try:
            processing_lock.release()
        except Exception:
            pass


def _start_background_watcher(poll_interval: float = 3.0):
    def watcher():
        seen = set()
        try:
            if os.path.exists(DB_FILE):
                df0 = pd.read_csv(DB_FILE)
                seen = set(df0['Filename'].tolist())
        except Exception:
            seen = set()

        while True:
            try:
                current = set(f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))) if os.path.exists(IMAGE_DIR) else set()
                new = sorted(list(current - seen))
                if new:
                    try:
                        process_and_log_images()
                    except Exception:
                        pass
                    try:
                        if os.path.exists(DB_FILE):
                            dfn = pd.read_csv(DB_FILE)
                            seen = set(dfn['Filename'].tolist())
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(poll_interval)

    t = threading.Thread(target=watcher, daemon=True)
    t.start()


def get_latest_metrics():
    if not os.path.exists(DB_FILE):
        return None
    try:
        df = pd.read_csv(DB_FILE)
        if df.empty:
            return None
        df['FileTime'] = df['Filename'].apply(lambda f: os.path.getmtime(os.path.join(IMAGE_DIR, f)) if os.path.exists(os.path.join(IMAGE_DIR, f)) else 0)
        df = df.sort_values(by='FileTime').drop(columns=['FileTime'])
        latest = df.iloc[-1].to_dict()
        return latest, df
    except Exception:
        return None


if 'watcher_running' not in st.session_state:
    try:
        _start_background_watcher()
        st.session_state['watcher_running'] = True
    except Exception:
        st.session_state['watcher_running'] = False


engine_result = get_latest_metrics()

if engine_result is not None:
    current_metrics, complete_history = engine_result

    t1_pct = current_metrics['Tub 1 Duckweed %']
    t2_pct = current_metrics['Tub 2 Duckweed %']

    st.subheader("⚠️ System Threshold Status")
    alert_triggered = False
    if t1_pct >= 80.0:
        st.error(f"🚨 **HARVEST ALERT:** Tub 1 (Left Mesocosm) has hit {t1_pct}%.")
        alert_triggered = True
    if t2_pct >= 80.0:
        st.error(f"🚨 **HARVEST ALERT:** Tub 2 (Right Mesocosm) has hit {t2_pct}%.")
        alert_triggered = True
    if not alert_triggered:
        st.success("✅ Growth volume nominal. All cultivation zones below 80%.")

    st.write("---")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Tub 1 (Left Mesocosm) Duckweed Density", value=f"{t1_pct}%")
    with col2:
        st.metric(label="Tub 2 (Right Mesocosm) Duckweed Density", value=f"{t2_pct}%")

    st.write("---")

    col_view, col_timeline = st.columns([1, 1])
    with col_view:
        st.subheader("📸 Current Active Mask Feed")
        live_image_path = os.path.join(LIVE_DIR, "live_stream_feed.jpg")
        if os.path.exists(live_image_path):
            st.image(live_image_path, caption=f"Source Frame: {current_metrics['Filename']}", width='stretch')
        else:
            st.info("Live feed image not yet generated. Processing first image...")

    with col_timeline:
        st.subheader("📈 Chronological Biomass Growth Curve")
        chart_df = complete_history.copy()
        chart_df['Sample Reference'] = "Img " + (chart_df.index + 1).astype(str) + " (" + chart_df['Filename'] + ")"
        chart_data = chart_df[['Sample Reference', 'Tub 1 Duckweed %', 'Tub 2 Duckweed %']].set_index('Sample Reference')
        st.line_chart(chart_data)

        with st.expander("📂 View Local Spreadsheet Database Logs"):
            st.dataframe(complete_history.sort_values(by='Timestamp', ascending=False), width='stretch')
else:
    st.warning("Awaiting target data frames. Drop valid images into 'duckweed_images/' to start analysis.")
