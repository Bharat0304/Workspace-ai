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

def detect_educational_content(text: str) -> tuple[bool, list[str]]:
    """Detect if content is educational and should be allowed"""
    if not text:
        return False, []
    
    text_lower = text.lower()
    
    # Comprehensive educational keywords
    educational_keywords = [
        # Core academic subjects
        "mathematics", "math", "calculus", "algebra", "geometry", "trigonometry",
        "statistics", "probability", "discrete math", "linear algebra",
        "physics", "chemistry", "biology", "science", "engineering", 
        "computer science", "programming", "coding", "software",
        
        # Programming languages and tech
        "python", "javascript", "java", "c++", "react", "node.js", "html", "css",
        "machine learning", "artificial intelligence", "data science", "algorithms",
        
        # Educational terms
        "tutorial", "learn", "education", "educational", "study", "studying",
        "lecture", "course", "class", "lesson", "academic", "university",
        "college", "school", "instructor", "professor", "teacher",
        
        # Learning platforms and institutions
        "khan academy", "coursera", "edx", "udemy", "mit", "stanford", 
        "harvard", "opencourseware", "codecademy", "freecodecamp",
        
        # Educational content indicators
        "how to", "explanation", "guide", "introduction to", "basics of",
        "fundamentals", "concepts", "theory", "practice", "examples",
        "solved", "problem solving", "step by step", "demonstration",
        "walkthrough", "explained", "understanding",
        
        # Subject-specific terms
        "calculus for engineering", "organic chemistry", "data structures",
        "web development", "machine learning course", "physics explained",
        "programming tutorial", "math help", "study guide",
        
        # Educational YouTube channels (common ones)
        "3blue1brown", "crash course", "ted-ed", "khan academy",
        "mit opencourseware", "professor leonard", "organic chemistry tutor",
        "patrickjmt", "the coding train", "sentdex", "corey schafer",
        "integration", "derivative", "formula", "equation"
    ]
    
    # Check for educational content
    detected_keywords = []
    education_score = 0
    
    for keyword in educational_keywords:
        if keyword in text_lower:
            detected_keywords.append(keyword)
            # Give higher weight to specific educational terms
            if keyword in ["tutorial", "learn", "education", "course", "lecture", "explained"]:
                education_score += 2
            else:
                education_score += 1
    
    # Special patterns for educational content
    educational_patterns = [
        r"how to .+ (programming|coding|math|science|engineering)",
        r"(tutorial|guide|course) .+ (programming|coding|development)",
        r"(learn|learning) .+ (python|javascript|math|calculus|physics)",
        r"(introduction to|basics of) .+ (computer science|programming|mathematics)",
        r"(solving|solved) .+ (problems|equations|algorithms)",
        r"(step by step|walkthrough) .+ (tutorial|guide|explanation)"
    ]
    
    import re
    for pattern in educational_patterns:
        if re.search(pattern, text_lower):
            education_score += 3
            detected_keywords.append(f"pattern_{pattern[:20]}...")
    
    is_educational = education_score >= 2  # Need at least 2 points to be considered educational
    
    return is_educational, detected_keywords

def detect_high_distraction_content(text: str) -> tuple[bool, list[str], int]:
    """Detect high distraction content that should be immediately blocked"""
    if not text:
        return False, [], 0
    
    text_lower = text.lower()
    
    # HIGH DISTRACTION: Entertainment content that should be IMMEDIATELY BLOCKED
    high_distraction_keywords = [
        # Comedy and Entertainment (IMMEDIATE BLOCK)
        'funny', 'memes', 'viral', 'comedy', 'hilarious', 'laugh', 'lol',
        'prank', 'pranks', 'fail', 'fails', 'compilation', 'reaction', 'roast',
        'entertainment', 'gossip', 'drama', 'scandal', 'cringe',
        
        # Music and Party Content
        'music video', 'song', 'dance', 'party', 'club', 'concert',
        'remix', 'beat', 'lyrics', 'album',
        
        # Ranking and List Content (often entertainment)
        'top 10', 'top 5', 'best of', 'worst of', 'vs', 'versus',
        'ranking', 'countdown', 'tier list',
        
        # Gaming Entertainment (non-educational)
        'gameplay', 'gaming', 'streamer', 'let\'s play', 'speedrun',
        'game review', 'gaming news', 'twitch', 'stream highlight',
        'montage', 'clips',
        
        # Social Media Content
        'tiktok', 'tiktoker', 'influencer', 'vlog', 'daily vlog',
        'lifestyle', 'day in my life', 'grwm', 'outfit',
        
        # Clickbait and Sensational Content
        'shocking', 'unbelievable', 'amazing', 'incredible', 'insane',
        'mind blown', 'you won\'t believe', 'gone wrong', 'gone wild'
    ]
    
    detected_keywords = []
    distraction_score = 0
    
    for keyword in high_distraction_keywords:
        if keyword in text_lower:
            detected_keywords.append(keyword)
            # Higher weight for clearly distracting content
            if keyword in ['funny', 'memes', 'viral', 'prank', 'fail', 'comedy', 'hilarious']:
                distraction_score += 5
            elif keyword in ['music video', 'gaming', 'entertainment', 'gossip']:
                distraction_score += 3
            else:
                distraction_score += 2
    
    # Check for distracting YouTube patterns
    high_distraction_patterns = [
        r"(funny|hilarious|comedy) .+ (video|compilation|moments)",
        r"(fail|epic fail) .+ (compilation|moments|videos)",
        r"(top \d+|best) .+ (funny|epic|fails|moments)",
        r"(reaction to|reacting to) .+ (video|song|movie)",
        r"(prank|pranking) .+ (people|friends|family)",
        r"(roasting|roast) .+ (people|celebrities|youtubers)",
        r"(gone wrong|gone wild|gone sexual)",
        r"(you won't believe|shocking|unbelievable)"
    ]
    
    import re
    for pattern in high_distraction_patterns:
        if re.search(pattern, text_lower):
            distraction_score += 4
            detected_keywords.append(f"pattern_{pattern[:25]}...")
    
    is_high_distraction = distraction_score >= 3  # Lower threshold for immediate blocking
    
    return is_high_distraction, detected_keywords, distraction_score

def detect_medium_distraction_content(text: str) -> tuple[bool, list[str]]:
    """Detect medium distraction content (social media, shopping, etc.)"""
    if not text:
        return False, []
    
    text_lower = text.lower()
    
    # Medium distraction keywords
    medium_distraction_keywords = [
        # Social media platforms
        'facebook', 'instagram', 'twitter', 'snapchat', 'linkedin',
        'social media', 'social', 'feed', 'timeline', 'posts', 'stories',
        'tweet', 'retweet', 'hashtag', 'follow', 'followers',
        
        # Shopping and commercial
        'shopping', 'buy', 'sale', 'deal', 'discount', 'product review',
        'unboxing', 'haul', 'amazon', 'flipkart', 'myntra', 'ebay',
        'price', 'offers', 'cart', 'checkout',
        
        # News and casual browsing (non-educational)
        'breaking news', 'celebrity news', 'sports news', 'latest news',
        'entertainment news', 'gossip news', 'politics', 'election',
        
        # Time-wasting activities
        'reddit', 'meme', 'chat', 'messaging', 'whatsapp', 'telegram'
    ]
    
    detected_keywords = []
    
    for keyword in medium_distraction_keywords:
        if keyword in text_lower:
            detected_keywords.append(keyword)
    
    is_medium_distraction = len(detected_keywords) > 0
    
    return is_medium_distraction, detected_keywords

def analyze_screen_from_b64(screenshot_b64: str) -> Dict[str, Any]:
    """OCR + simple heuristics + optional model classification + educational content detection.
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

    website = extract_website(ocr_text) if ocr_text else "unknown"
    task = extract_tab_title(ocr_text) if ocr_text else ""
    
    print(f"🌐 Detected website: {website}")
    print(f"📝 Detected task/title: {task}")

    # First check for educational content
    is_educational, educational_keywords = detect_educational_content(ocr_text)
    
    if is_educational:
        print(f"🎓 EDUCATIONAL CONTENT DETECTED: {educational_keywords}")
        return {
            "is_distraction": False,
            "distraction_score": 0,
            "productivity_score": 100,
            "recommendations": ["Great! Keep learning! 📚"],
            "content_type": "educational",
            "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "saved_screenshot": saved_file,
            "extracted_text": ocr_text[:500] if ocr_text else "",
            "detected_keywords": educational_keywords,
            "detection_method": "educational_override",
            "ocr_confidence": len(ocr_text) > 10,
            "override_reason": "educational_content"
        }

    # Check for high distraction content
    is_high_distraction, high_keywords, high_score = detect_high_distraction_content(ocr_text)
    
    if is_high_distraction:
        print(f"🚨 HIGH DISTRACTION DETECTED: {high_keywords}")
        return {
            "is_distraction": True,
            "distraction_score": min(95, high_score * 10),
            "productivity_score": 5,
            "recommendations": ["Entertainment content blocked! Close this and focus on your studies."],
            "content_type": "high_distraction",
            "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "saved_screenshot": saved_file,
            "extracted_text": ocr_text[:500] if ocr_text else "",
            "detected_keywords": high_keywords,
            "detection_method": "high_distraction_blocking",
            "ocr_confidence": len(ocr_text) > 10,
            "blocking_reason": f"Entertainment keywords: {', '.join(high_keywords[:3])}"
        }

    # Check for medium distraction content
    is_medium_distraction, medium_keywords = detect_medium_distraction_content(ocr_text)
    
    if is_medium_distraction:
        print(f"⚠️ MEDIUM DISTRACTION DETECTED: {medium_keywords}")
        return {
            "is_distraction": True,
            "distraction_score": 60,
            "productivity_score": 40,
            "recommendations": ["Social media detected. Consider focusing on your tasks."],
            "content_type": "medium_distraction",
            "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "saved_screenshot": saved_file,
            "extracted_text": ocr_text[:500] if ocr_text else "",
            "detected_keywords": medium_keywords,
            "detection_method": "medium_distraction_detected",
            "ocr_confidence": len(ocr_text) > 10,
        }

    # Optional: model prediction for edge cases
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

    # Default to productive if no distractions detected
    is_distraction = (label == "Distraction") if label else False
    distraction_score = 70 if is_distraction else 10
    productivity_score = 30 if is_distraction else 90
    
    print(f"📊 Final result: {'🚨 DISTRACTION' if is_distraction else '✅ PRODUCTIVE'}")

    # Enhanced recommendations
    recommendations = []
    if is_distraction:
        recommendations.append("Potential distraction detected. Stay focused on your goals.")
    else:
        recommendations.append("Great focus! Keep up the good work.")

    result = {
        "is_distraction": is_distraction,
        "distraction_score": distraction_score,
        "productivity_score": productivity_score,
        "recommendations": recommendations,
        "content_type": "neutral",
        "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "saved_screenshot": saved_file,
        "extracted_text": ocr_text[:500] if ocr_text else "",
        "detected_keywords": [],
        "detection_method": "model" if label else "neutral",
        "ocr_confidence": len(ocr_text) > 10,
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
    """Enhanced window-based distraction detection with strict entertainment blocking"""
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
    
    # Combine all text for analysis
    all_text = f"{title} {url}".strip()
    
    # FIRST: Check for educational content (highest priority)
    is_educational, educational_indicators = detect_educational_content(all_text)
    
    if is_educational:
        print(f"🎓 EDUCATIONAL CONTENT DETECTED: {educational_indicators}")
        print(f"📚 Content classified as LEARNING MATERIAL")
        
        return {
            "is_distraction": False,
            "distraction_score": 0,
            "suggested_action": None,
            "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "detected_indicators": educational_indicators,
            "content_type": "educational",
            "severity": "none",
            "active_time_seconds": active_time,
            "should_alert": False,
            "should_block": False,
            "should_warn": False,
            "should_close": False,
            "override_reason": "educational_content",
            "recommendation": "Great! Keep learning! 📚"
        }
    
    # SECOND: Check for HIGH DISTRACTION entertainment content (STRICT)
    is_high_distraction, high_keywords, high_score = detect_high_distraction_content(all_text)
    
    # AGGRESSIVE: If ANY high distraction keywords found, IMMEDIATELY BLOCK
    if is_high_distraction:
        print(f"🚨 HIGH DISTRACTION DETECTED: {high_keywords}")
        print(f"⚡ IMMEDIATE BLOCKING TRIGGERED - Score: {high_score}")
        
        return {
            "is_distraction": True,
            "distraction_score": min(95, 80 + high_score),  # Very high score
            "suggested_action": "force-close",
            "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "detected_indicators": high_keywords,
            "content_type": "high_distraction",
            "severity": "critical",  # Critical severity
            "active_time_seconds": active_time,
            "should_alert": True,
            "should_block": True,    # Immediate block
            "should_warn": False,    # Skip warning phase
            "should_close": True,    # Can close immediately
            "override_reason": "entertainment_detected",
            "recommendation": "Entertainment content blocked! Time to focus on your studies!",
            "blocking_reason": f"Entertainment keywords detected: {', '.join(high_keywords[:3])}",
            "warning_message": f"🚫 Entertainment Blocked: {', '.join(high_keywords[:2])}"
        }
    
    # THIRD: Check for medium distraction content
    is_medium_distraction, medium_keywords = detect_medium_distraction_content(all_text)
    
    # Handle YouTube with special logic (if not already caught above)
    is_youtube = "youtube" in url
    if is_youtube and not is_educational and not is_high_distraction:
        print(f"📺 YOUTUBE DETECTED - Neutral content analysis...")
        
        if medium_keywords:
            # Medium distraction - progressive blocking
            distraction_score = 60
            severity = "medium"
            is_distraction = True
        else:
            # Neutral YouTube content - allow but monitor
            print(f"📺 YouTube content appears neutral - allowing with monitoring")
            distraction_score = 20
            severity = "low"
            is_distraction = False
    else:
        # Non-YouTube sites
        if is_medium_distraction:
            is_distraction = True
            distraction_score = min(75, len(medium_keywords) * 15)
            severity = "medium"
        else:
            is_distraction = False
            distraction_score = 5
            severity = "none"
    
    # For medium distractions, use progressive blocking based on time
    if is_medium_distraction or (is_youtube and medium_keywords):
        detected_indicators = medium_keywords
        
        if active_time > 120:  # 2 minutes
            should_block = True
            should_close = True
            severity = "high"
            suggested_action = "close-tab"
        elif active_time > 30:  # 30 seconds  
            should_block = True
            should_close = False
            severity = "medium"
            suggested_action = "warning"
        else:
            should_block = False
            should_close = False
            severity = "low"
            suggested_action = "monitor"
            
        recommendation = f"Social media/distraction detected. Focus on your studies!"
        
        return {
            "is_distraction": is_distraction,
            "distraction_score": distraction_score,
            "suggested_action": suggested_action,
            "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "detected_indicators": detected_indicators,
            "content_type": "medium_distraction",
            "severity": severity,
            "active_time_seconds": active_time,
            "should_alert": is_distraction,
            "should_block": should_block,
            "should_warn": not should_block and is_distraction,
            "should_close": should_close,
            "recommendation": recommendation,
            "warning_message": f"⚠️ Distraction Alert: {', '.join(detected_indicators[:2])}"
        }
    
    # If no distractions detected
    print(f"📊 Window distraction result: ✅ PRODUCTIVE")
    print(f"🎯 No distracting content detected")
    
    return {
        "is_distraction": False,
        "distraction_score": 5,
        "suggested_action": None,
        "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "detected_indicators": [],
        "content_type": "neutral",
        "severity": "none",
        "active_time_seconds": active_time,
        "should_alert": False,
        "should_block": False,
        "should_warn": False,
        "should_close": False,
        "recommendation": "Good focus! Keep up the productive work.",
        "educational_indicators": educational_indicators if educational_indicators else []
    }
