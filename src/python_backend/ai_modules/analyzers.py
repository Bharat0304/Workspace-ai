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

def _save_screenshot_debug(b64_data: str) -> str:
    """Save screenshot for debugging if enabled"""
    if os.getenv('SAVE_SCREENSHOTS', 'false').lower() != 'true':
        return ""
    
    try:
        # Create screenshots directory
        screenshots_dir = os.path.join(os.getcwd(), 'screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Decode and save
        image_data = base64.b64decode(b64_data)
        timestamp = __import__("datetime").datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = f'screenshot_{timestamp}.png'
        filepath = os.path.join(screenshots_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        print(f"📸 Screenshot saved: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Failed to save screenshot: {e}")
        return ""

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

def detect_distracting_keywords(text: str) -> tuple[bool, list[str]]:
    """Enhanced distraction keyword detection"""
    if not text:
        return False, []
    
    text_lower = text.lower()
    
    # Comprehensive distraction keywords
    distraction_keywords = {
        # Social Media
        'youtube', 'facebook', 'instagram', 'twitter', 'tiktok', 'snapchat', 
        'reddit', 'linkedin', 'whatsapp', 'telegram', 'discord', 'pinterest',
        
        # Entertainment
        'netflix', 'hulu', 'disney+', 'amazon prime', 'spotify', 'soundcloud',
        'twitch', 'gaming', 'game', 'video', 'movie', 'series', 'entertainment',
        'funny', 'meme', 'viral', 'trending', 'comedy', 'music',
        
        # Shopping
        'amazon', 'ebay', 'shopping', 'cart', 'buy', 'purchase', 'deals',
        'flipkart', 'myntra', 'zomato', 'swiggy',
        
        # News & Random Browsing
        'news', 'breaking', 'headlines', 'gossip', 'celebrity', 'sports',
        
        # Common UI Elements of Distracting Sites
        'subscribe', 'like', 'comment', 'share', 'follow', 'notification',
        'trending now', 'recommended', 'watch later', 'playlist'
    }
    
    detected_keywords = []
    for keyword in distraction_keywords:
        if keyword in text_lower:
            detected_keywords.append(keyword)
    
    is_distraction = len(detected_keywords) > 0
    
    # Special case: Strong YouTube indicators
    youtube_indicators = ['youtube', 'subscribe', 'like and subscribe', 'watch later', 'recommended']
    youtube_score = sum(1 for indicator in youtube_indicators if indicator in text_lower)
    
    if youtube_score >= 2:  # Multiple YouTube indicators
        is_distraction = True
        print(f"🚨 Strong YouTube indicators detected: {youtube_score}")
    
    return is_distraction, detected_keywords

def analyze_screen_from_b64(screenshot_b64: str) -> Dict[str, Any]:
    """OCR + simple heuristics + optional model classification.
    Returns dict fields expected by Node (see PythonAnalysisResponse).
    """
    # Save screenshot for debugging
    saved_file = _save_screenshot_debug(screenshot_b64)
    
    img_np = _b64_to_image_np(screenshot_b64)

    # OCR (graceful fallback if deps missing)
    ocr_text = ""
    if cv2 is not None and pytesseract is not None:
        try:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            ocr_text = pytesseract.image_to_string(thresh)
            print(f"🔍 OCR extracted ({len(ocr_text)} chars): {ocr_text[:100]}...")
        except Exception as e:
            print(f"❌ OCR failed: {e}")
    else:
        print("❌ OCR dependencies missing (cv2 or pytesseract)")
        print("   Install with: sudo apt-get install tesseract-ocr (Linux)")
        print("   Install with: brew install tesseract (macOS)")

    website = extract_website(ocr_text) if ocr_text else "unknown"
    task = extract_tab_title(ocr_text) if ocr_text else ""
    
    print(f"🌐 Detected website: {website}")
    print(f"📝 Detected task/title: {task}")

    # Enhanced distraction detection
    keyword_distraction, detected_keywords = detect_distracting_keywords(ocr_text)
    print(f"🎯 Keyword analysis: {keyword_distraction}, found: {detected_keywords}")

    # Optional: model prediction
    label = None
    model = _ensure_model(None)
    if model is not None:
        try:
            import pandas as pd  # type: ignore
            sample_df = pd.DataFrame([{"Website": website, "Extracted_Text": task}])
            pred = model.predict(sample_df)
            label = "Task" if int(pred[0]) == 0 else "Distraction"
            print(f"🤖 Model prediction: {label}")
        except Exception as e:
            print(f"❌ Model prediction failed: {e}")
            label = None

    # Combine all detection methods
    # Priority: Model > Keywords > Heuristics
    if label is not None:
        is_distraction = (label == "Distraction")
        detection_method = "model"
    else:
        is_distraction = keyword_distraction
        detection_method = "keywords"
    
    # Additional heuristic: if website is known to be distracting
    distracting_sites = ['youtube.com', 'facebook.com', 'instagram.com', 'twitter.com', 
                        'netflix.com', 'reddit.com', 'tiktok.com']
    if website in distracting_sites:
        is_distraction = True
        detection_method = "website_match"
    
    print(f"🎯 Final detection method: {detection_method}")
    print(f"📊 Final result: {'🚨 DISTRACTION' if is_distraction else '✅ PRODUCTIVE'}")

    # Map to fields expected by Node side
    distraction_score = 80 if is_distraction else 10
    productivity_score = 30 if is_distraction else 80
    
    # Enhanced recommendations
    recommendations = []
    if is_distraction:
        if 'youtube' in detected_keywords:
            recommendations.append("Close YouTube and return to studying")
        elif any(social in detected_keywords for social in ['facebook', 'instagram', 'twitter']):
            recommendations.append("Close social media and focus on your tasks")
        elif any(entertainment in detected_keywords for entertainment in ['netflix', 'gaming', 'music']):
            recommendations.append("Close entertainment apps and concentrate")
        else:
            recommendations.append("Close distracting tab and refocus")
        
        recommendations.append("Consider using website blockers during study time")
    else:
        recommendations.append("Great focus! Keep up the good work")

    result = {
        "is_distraction": is_distraction,
        "distraction_score": distraction_score,
        "productivity_score": productivity_score,
        "recommendations": recommendations,
        "content_type": website,
        "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "saved_screenshot": saved_file,
        "extracted_text": ocr_text[:500] if ocr_text else "",
        "detected_keywords": detected_keywords,
        "detection_method": detection_method,
        "ocr_confidence": len(ocr_text) > 10,  # Simple confidence based on text length
    }

    return result

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
    """Enhanced window-based distraction detection"""
    title = ""
    process_name = ""
    url = ""
    
    if isinstance(window_info, dict):
        title = window_info.get("title", "").lower()
        process_name = window_info.get("process_name", "").lower() 
        url = window_info.get("url", "").lower()
        active_time = window_info.get("active_time", 0)
    else:
        active_time = 0
    
    print(f"🔍 Window analysis - Title: {title[:50]}...")
    print(f"🔍 Window analysis - Process: {process_name}")
    print(f"🔍 Window analysis - URL: {url[:50]}...")
    print(f"🔍 Window analysis - Active time: {active_time}s")
    
    # Enhanced distraction detection
    distraction_indicators = [
        # Video & Entertainment
        "youtube", "netflix", "hulu", "disney", "amazon prime", "twitch",
        "video", "movie", "series", "streaming",
        
        # Social Media
        "facebook", "instagram", "twitter", "tiktok", "snapchat", "linkedin",
        "social", "chat", "messaging",
        
        # Gaming
        "game", "gaming", "steam", "epic games", "minecraft", "fortnite",
        
        # Shopping
        "shopping", "amazon", "ebay", "cart", "buy", "purchase",
        
        # News & Browsing
        "news", "reddit", "9gag", "memes", "funny", "entertainment"
    ]
    
    # Check all sources
    all_text = f"{title} {process_name} {url}".lower()
    detected_distractions = []
    
    for indicator in distraction_indicators:
        if indicator in all_text:
            detected_distractions.append(indicator)
    
    is_distraction = len(detected_distractions) > 0
    
    # Calculate severity based on active time and type
    if is_distraction:
        if active_time > 300:  # 5 minutes
            severity = "high"
            distraction_score = 90
        elif active_time > 60:  # 1 minute
            severity = "medium" 
            distraction_score = 75
        else:
            severity = "low"
            distraction_score = 60
    else:
        severity = "none"
        distraction_score = 5
    
    # Determine suggested action
    suggested_action = None
    if is_distraction:
        if active_time > 300:
            suggested_action = "force-close"
        elif active_time > 60:
            suggested_action = "close-tab"
        else:
            suggested_action = "warning"
    
    print(f"📊 Window distraction result: {'🚨 DISTRACTION' if is_distraction else '✅ PRODUCTIVE'}")
    print(f"🎯 Detected: {detected_distractions}")
    print(f"⚠️  Severity: {severity}, Score: {distraction_score}")
    
    result = {
        "is_distraction": is_distraction,
        "distraction_score": distraction_score,
        "suggested_action": suggested_action,
        "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "detected_indicators": detected_distractions,
        "severity": severity,
        "active_time_seconds": active_time,
        "should_alert": is_distraction and active_time > 10,
        "should_block": is_distraction and active_time > 180,  # 3 minutes
    }
    
    return result
