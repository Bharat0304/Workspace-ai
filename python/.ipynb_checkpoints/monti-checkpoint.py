# app.py
import streamlit as st
import re
import pandas as pd
import time
import cv2
import pytesseract
import numpy as np
import pyautogui
import joblib

def extract_website(ocr_text: str) -> str:
    # Regex to capture domains like youtube.com, instagram.com, x.com, etc.
    match = re.search(r"\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|io|co|in|ai|gov|edu)\b", ocr_text.lower())
    
    if match:
        return match.group(0)
    
    return "unknown"

def extract_tab_title(ocr_text: str) -> str:
    # Split into lines and clean
    lines = [line.strip() for line in ocr_text.split("\n") if line.strip()]
    
    if not lines:
        return ""
    
    # Usually the first meaningful line contains tab title
    first_line = lines[0]
    
    # Remove stray OCR junk symbols at start/end
    clean_title = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", first_line)
    
    return clean_title
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Assuming you have these functions already
# from your previous code
# extract_website(ocr_text), extract_tab_title(ocr_text)
# clf_pipeline → your trained classifier

st.title("Focus & Distraction Monitoring")

# Interval setting
interval = st.slider("Select screenshot interval (seconds)", 60, 600, 300)  # default 5 min

# DataFrame to hold results
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Website", "Task", "Label", "Timestamp"])

def capture_screenshot():
    """
    Capture full screen as numpy array
    """
    screenshot = pyautogui.screenshot()
    return np.array(screenshot)

def process_screenshot(image, clf_pipeline):
    """
    OCR -> Extract website & task -> Predict Task/Distraction
    """
    # OCR
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    ocr_text = pytesseract.image_to_string(thresh)

    # Extract website & task
    website = extract_website(ocr_text)
    task = extract_tab_title(ocr_text)

    # Predict
    sample_df = pd.DataFrame([{"Website": website, "Extracted_Text": task}])
    pred = clf_pipeline.predict(sample_df)
    label = "Task" if pred[0]==0 else "Distraction"

    return website, task, label
clf_pipeline = joblib.load("distraction_model.pkl")
# Start monitoring
if st.button("Start Monitoring"):
    st.info("Monitoring started. Press Stop to end.")
    while True:
        # Capture
        screenshot = capture_screenshot()

        # Process
        website, task, label = process_screenshot(screenshot, clf_pipeline)

        # Add timestamp
        timestamp = pd.Timestamp.now()

        # Append to session_state DataFrame
        st.session_state.df = pd.concat([
            st.session_state.df,
            pd.DataFrame([{
                "Website": website,
                "Task": task,
                "Label": label,
                "Timestamp": timestamp
            }])
        ], ignore_index=True)

        # Display latest
        st.write(st.session_state.df.tail(5))

        # Wait interval
        time.sleep(interval)


