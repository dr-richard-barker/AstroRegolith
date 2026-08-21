import streamlit as st
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import json
import os

# Set page config
st.set_page_config(
    page_title="AstroBotany PlantCV Segmentation GUI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom minimal zinc/teal styles
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}
code, pre, [class*="mono"] {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
}

/* Custom card container */
.zinc-card {
    border: 1px solid #e4e4e7;
    border-radius: 8px;
    padding: 18px;
    background-color: #ffffff;
    margin-bottom: 14px;
}
.kpi-container {
    display: flex;
    gap: 16px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}
.kpi-card {
    flex: 1 1 200px;
    border: 1px solid #e4e4e7;
    border-radius: 8px;
    padding: 16px;
    background-color: #fafafa;
    text-align: center;
}
.kpi-val {
    font-size: 1.8rem;
    font-weight: 700;
    color: #0d9488; /* Teal */
    margin: 4px 0;
}
.kpi-lbl {
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #71717a;
}
</style>
""", unsafe_allow_html=True)

st.title("🌱 AstroBotany PlantCV Analysis GUI")
st.subheader("Semi-automated leaf and duckweed segmentation pipeline")

# Check if PlantCV is installed
try:
    from plantcv import plantcv as pcv
    # Set default configuration
    pcv.params.debug = None
    plantcv_available = True
except ImportError:
    plantcv_available = False

if not plantcv_available:
    st.error("""
    **PlantCV is not installed in the active environment.**
    Please run the following commands in your terminal to install the dependencies:
    ```bash
    uv pip install plantcv streamlit opencv-python-headless matplotlib pandas numpy
    ```
    """)
    st.stop()

# Helper: Load and decode image
@st.cache_data
def load_image(uploaded_file):
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Setup Sidebar
st.sidebar.header("📁 Input Image")
uploaded_file = st.sidebar.file_uploader(
    "Choose a plant or duckweed image...", 
    type=["jpg", "jpeg", "png", "tif", "tiff"]
)

st.sidebar.header("⚙️ Segmentation Settings")
color_space = st.sidebar.selectbox("Color Space", ["HSV", "Lab"])

if color_space == "HSV":
    channel = st.sidebar.selectbox("Channel", ["Saturation", "Hue", "Value"])
    channel_index = {"Hue": "h", "Saturation": "s", "Value": "v"}[channel]
else:
    channel = st.sidebar.selectbox("Channel", ["A (green-red)", "B (blue-yellow)", "L (lightness)"])
    channel_index = {"L": "l", "A": "a", "B": "b"}[channel.split()[0]]

threshold_val = st.sidebar.slider("Threshold Value", 0, 255, 120)
threshold_type = st.sidebar.radio("Threshold Direction", ["Detect bright objects", "Detect dark objects"])

st.sidebar.header("🧹 Cleanup Filters")
fill_holes = st.sidebar.slider("Fill Small Holes (Max Area)", 0, 500, 100)
erode_size = st.sidebar.slider("Erosion Kernel Size", 0, 10, 0)
dilate_size = st.sidebar.slider("Dilation Kernel Size", 0, 10, 0)

st.sidebar.header("📏 Scale Calibration")
calibration_mode = st.sidebar.selectbox("Calibration Mode", ["Pixels only", "Manual scale (px/cm)"])

px_per_cm = 1.0
if calibration_mode == "Manual scale (px/cm)":
    px_per_cm = st.sidebar.number_input("Pixels per cm", min_value=1.0, value=100.0, step=10.0)

# Main workflow execution
if uploaded_file is not None:
    filename = uploaded_file.name
    img = load_image(uploaded_file)
    
    # Run PlantCV processing steps
    # 1. Convert to target channel
    if color_space == "HSV":
        channels = pcv.rgb2gray_hsv(rgb_img=img, channel=channel_index)
    else:
        channels = pcv.rgb2gray_lab(rgb_img=img, channel=channel_index)
        
    # 2. Binary Thresholding
    obj_type = "light" if threshold_type == "Detect bright objects" else "dark"
    bin_mask = pcv.threshold.binary(gray_img=channels, threshold=threshold_val, max_value=255, object_type=obj_type)
    
    # 3. Clean up noise
    cleaned = bin_mask.copy()
    if fill_holes > 0:
        cleaned = pcv.fill(bin_mask=cleaned, size=fill_holes)
    if erode_size > 0:
        kernel = np.ones((erode_size, erode_size), np.uint8)
        cleaned = cv2.erode(cleaned, kernel, iterations=1)
    if dilate_size > 0:
        kernel = np.ones((dilate_size, dilate_size), np.uint8)
        cleaned = cv2.dilate(cleaned, kernel, iterations=1)
        
    # 4. Find and filter objects (contours)
    contours, hierarchy = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter out very small contours (under 10 px area) to avoid noise counts
    min_area = 10
    filtered_contours = [c for c in contours if cv2.contourArea(c) >= min_area]
    
    # Draw contours and label count index overlay
    output_img = img.copy()
    contour_data = []
    
    for idx, c in enumerate(filtered_contours):
        area_px = cv2.contourArea(c)
        perimeter = cv2.arcLength(c, True)
        
        # Calculate moments for centroid
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
        else:
            cx, cy = 0, 0
            
        # Draw magenta outline
        cv2.drawContours(output_img, [c], -1, (255, 0, 255), 2)
        # Put numbering text
        cv2.putText(output_img, str(idx + 1), (cx - 10, cy - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Area conversion
        area_cm2 = area_px / (px_per_cm ** 2)
        
        contour_data.append({
            "Leaf ID": idx + 1,
            "Area (px)": area_px,
            "Area (cm²)": round(area_cm2, 4),
            "Centroid X": cx,
            "Centroid Y": cy
        })
        
    total_area_px = sum(d["Area (px)"] for d in contour_data)
    total_area_cm2 = total_area_px / (px_per_cm ** 2)
    avg_area_cm2 = total_area_cm2 / len(filtered_contours) if filtered_contours else 0.0
    
    # Setup tabs
    tab_pipeline, tab_results, tab_code = st.tabs(["🖼️ Image Pipeline", "📊 Quantification & Results", "💻 PlantCV Code Snippet"])
    
    with tab_pipeline:
        col1, col2 = st.columns(2)
        with col1:
            st.image(img, caption="Original Image", use_container_width=True)
            st.image(channels, caption=f"Grayscale Channel ({color_space} - {channel})", use_container_width=True)
        with col2:
            st.image(cleaned, caption="Cleaned Binary Mask", use_container_width=True)
            st.image(output_img, caption="Segmented Leaf Outline & Index Labeled Overlay", use_container_width=True)
            
    with tab_results:
        # Display KPI cards
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-lbl">Total Leaves / Fronds</div>
                <div class="kpi-val">{len(filtered_contours)}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-lbl">Total Surface Area</div>
                <div class="kpi-val">{round(total_area_cm2, 2) if calibration_mode != "Pixels only" else total_area_px} <span style="font-size:1rem;font-weight:normal;">{ 'cm²' if calibration_mode != 'Pixels only' else 'px' }</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-lbl">Average Leaf Size</div>
                <div class="kpi-val">{round(avg_area_cm2, 4) if calibration_mode != "Pixels only" else round(total_area_px / len(filtered_contours), 1) if filtered_contours else 0} <span style="font-size:1rem;font-weight:normal;">{ 'cm²' if calibration_mode != 'Pixels only' else 'px' }</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### Segmented Leaf Contours Table")
        if contour_data:
            df = pd.DataFrame(contour_data)
            st.dataframe(df, use_container_width=True)
            
            # Export Sidecar Metadata
            st.markdown("### Export Metadata Sidecar")
            st.write("Generate a sidecar CSV matching the database schema to accompany your dataset.")
            
            # Infer biological properties
            parts = filename.split(/[_-]/)
            inferred_species = "Landoltia punctata" if "londultia" in filename.lower() or "landoltia" in filename.lower() else "Arabidopsis thaliana"
            
            meta_row = {
                "filename": filename,
                "species": inferred_species,
                "genotype": parts[3] if len(parts) >= 4 else "Col-0",
                "treatment": parts[0] + "_" + parts[1] if len(parts) >= 2 else "Control",
                "scale_bar_mm": round((px_per_cm * 10), 1) if calibration_mode != "Pixels only" else 0.0,
                "leaf_count": len(filtered_contours),
                "leaf_area_cm2": round(total_area_cm2, 4)
            }
            
            df_sidecar = pd.DataFrame([meta_row])
            csv_buf = BytesIO()
            df_sidecar.to_csv(csv_buf, index=False)
            csv_data = csv_buf.getvalue()
            
            st.download_button(
                label="📥 Download metadata.csv Sidecar",
                data=csv_data,
                file_name=f"{filename.split('.')[0]}_metadata.csv",
                mime="text/csv"
            )
        else:
            st.warning("No plant contours detected. Try adjusting the segmentation parameters in the sidebar.")
            
    with tab_code:
        st.markdown("Copy this Python script snippet to reproduce this segmentation pipeline locally in code:")
        st.code(f"""
import cv2
import numpy as np
from plantcv import plantcv as pcv

# Load image
img = cv2.imread("{filename}")
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# 1. Convert color space channel
# Target color space: {color_space}, Channel: {channel}
gray_img = pcv.rgb2gray_{color_space.lower()}(rgb_img=img_rgb, channel="{channel_index}")

# 2. Binary Thresholding
bin_mask = pcv.threshold.binary(gray_img=gray_img, threshold={threshold_val}, max_value=255, object_type="{obj_type}")

# 3. Morphological Cleanup filters
cleaned = bin_mask
{"cleaned = pcv.fill(bin_mask=cleaned, size=" + str(fill_holes) + ")" if fill_holes > 0 else "# No fill filter applied"}
{"kernel_erode = np.ones((" + str(erode_size) + ", " + str(erode_size) + "), np.uint8)\\ncleaned = cv2.erode(cleaned, kernel_erode, iterations=1)" if erode_size > 0 else ""}
{"kernel_dilate = np.ones((" + str(dilate_size) + ", " + str(dilate_size) + "), np.uint8)\\ncleaned = cv2.dilate(cleaned, kernel_dilate, iterations=1)" if dilate_size > 0 else ""}

# 4. Find object contours
contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
filtered_contours = [c for c in contours if cv2.contourArea(c) >= 10]

print(f"Total counted leaves: {{len(filtered_contours)}}")
        """, language="python")

else:
    st.info("👈 Please upload a plant or duckweed photo in the sidebar to begin analysis!")
    
    # Show dynamic design demo
    st.markdown("""
    <div class="zinc-card">
        <h3>💡 How it works</h3>
        <p>This semi-automated GUI integrates <strong>PlantCV</strong> thresholding, channel selection, and contour analysis. Adjust the sliders in the left sidebar to calibrate contrast and segment leaves from the background, then download the structured sidecar metadata file ready for uploading.</p>
    </div>
    """, unsafe_allow_html=True)
