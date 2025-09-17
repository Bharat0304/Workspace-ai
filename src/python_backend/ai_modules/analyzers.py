import base64
import io
import os
from typing import Dict, Any, Tuple

import numpy as np
from PIL import Image

# Optional heavy deps (OCR / CV / ML). Import lazily where needed to avoid import errors
try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore

try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover
    joblib = None  # type: ignore


_MODEL = None


def _ensure_model(model_path: str | None = None):
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if joblib is None:
        return None
    # default expected location inside repo
    default_path = os.getenv("DISTRACTION_MODEL_PATH", os.path.join(os.path.dirname(__file__), "distraction_model.pkl"))
    model_path = model_path or default_path
    if os.path.exists(model_path):
        try:
            _MODEL = joblib.load(model_path)
        except Exception:
            _MODEL = None
    return _MODEL


def _b64_to_image_np(b64_data: str) -> np.ndarray:
    """Decode base64 image (jpeg/png) to numpy array in RGB."""
    raw = base64.b64decode(b64_data)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return np.array(img)


def extract_website(ocr_text: str) -> str:
    import re
    match = re.search(r"\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|io|co|in|ai|gov|edu)\b", ocr_text.lower())
    return match.group(0) if match else "unknown"


def extract_tab_title(ocr_text: str) -> str:
    lines = [line.strip() for line in ocr_text.split("\n") if line.strip()]
    if not lines:
        return ""
    first_line = lines[0]
    import re
    return re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", first_line)


def analyze_screen_from_b64(screenshot_b64: str) -> Dict[str, Any]:
    """OCR + simple heuristics + optional model classification.
    Returns dict fields expected by Node (see PythonAnalysisResponse).
    """
    img_np = _b64_to_image_np(screenshot_b64)

    # OCR (graceful fallback if deps missing)
    ocr_text = ""
    if cv2 is not None and pytesseract is not None:
        try:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            ocr_text = pytesseract.image_to_string(thresh)
        except Exception:
            pass

    website = extract_website(ocr_text) if ocr_text else "unknown"
    task = extract_tab_title(ocr_text) if ocr_text else ""

    # Optional: model prediction
    label = None
    model = _ensure_model(None)
    if model is not None:
        try:
            import pandas as pd  # type: ignore
            sample_df = pd.DataFrame([{"Website": website, "Extracted_Text": task}])
            pred = model.predict(sample_df)
            label = "Task" if int(pred[0]) == 0 else "Distraction"
        except Exception:
            label = None

    # Map to fields expected by Node side
    is_distraction = (label == "Distraction") if label is not None else False
    distraction_score = 80 if is_distraction else 10
    productivity_score = 30 if is_distraction else 80
    recommendations = ["close distracting tab"] if is_distraction else []

    return {
        "is_distraction": is_distraction,
        "distraction_score": distraction_score,
        "productivity_score": productivity_score,
        "recommendations": recommendations,
        "content_type": website,
        "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }


def analyze_focus_from_b64(frame_b64: str) -> Dict[str, Any]:
    """Mock focus analysis from a single frame. Extend with real model as needed."""
    size = len(frame_b64)
    focus_score = max(0, min(100, (size % 100)))
    levels = ["low", "medium", "high"]
    focus_level = levels[(size // 7) % 3]
    attention_level = levels[(size // 11) % 3]
    eye_gaze = ["left", "forward", "right"][ (size // 5) % 3 ]
    face_detected = (size % 2) == 0
    return {
        "focus_score": focus_score,
        "focus_level": focus_level,
        "attention_level": attention_level,
        "eye_gaze": eye_gaze,
        "face_detected": face_detected,
        "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "recommendations": ["blink more often", "adjust screen distance"] if focus_level == "low" else [],
    }


def analyze_distraction_from_window(window_info: Dict[str, Any]) -> Dict[str, Any]:
    title = None
    if isinstance(window_info, dict):
        title = window_info.get("title")
    distracted = bool(title and any(k in title.lower() for k in ["youtube", "netflix", "instagram"]))
    return {
        "is_distraction": distracted,
        "distraction_score": 75 if distracted else 5,
        "suggested_action": "close-tab" if distracted else None,
        "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
