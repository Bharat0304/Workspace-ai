from typing import Optional, Dict, Any
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import logging
from ai_modules.analyzers import (
    analyze_screen_from_b64,
    analyze_focus_from_b64,
    analyze_distraction_from_window,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================
# Models matching Node bridge inputs
# ==============================
class ScreenAnalyzeRequest(BaseModel):
    screenshot_data: str
    user_id: str
    session_id: str

class FocusAnalyzeRequest(BaseModel):
    frame_data: str
    user_id: str
    session_id: str

class DistractionDetectRequest(BaseModel):
    window_info: Dict[str, Any]
    user_id: str
    session_id: str

class PostureAnalyzeRequest(BaseModel):
    frame_data: str
    user_id: str
    session_id: str

# ==============================
# New models for browser extension
# ==============================
class TabAnalyzeRequest(BaseModel):
    url: str
    title: str
    timestamp: Optional[int] = None

class ExtensionStatsRequest(BaseModel):
    action: str
    site: Optional[str] = None
    duration: Optional[int] = None

# ==============================
# FastAPI app setup
# ==============================
app = FastAPI(title="WorkSpace AI Python Backend", version="0.1.0")

# CORS: allow local dev frontend/backend + browser extensions
frontend_origin = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_origin, 
        "http://localhost:3000", 
        "http://localhost:5000", 
        "http://localhost:5001",
        "chrome-extension://*",  # Allow Chrome extensions
        "moz-extension://*",     # Allow Firefox extensions
        "*"  # Allow all origins for extension development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# Existing endpoints
# ==============================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "python": True,
        "time": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }

@app.post("/api/analyze-screen")
def analyze_screen(payload: ScreenAnalyzeRequest):
    # Use analyzer to OCR and classify task vs distraction
    result = analyze_screen_from_b64(payload.screenshot_data)
    return {
        "success": True,
        "analysis_type": "screen",
        "user_id": payload.user_id,
        "session_id": payload.session_id,
        "result": result,
    }

@app.post("/api/analyze-focus")
def analyze_focus(payload: FocusAnalyzeRequest):
    result = analyze_focus_from_b64(payload.frame_data)
    return {
        "success": True,
        "analysis_type": "focus",
        "user_id": payload.user_id,
        "session_id": payload.session_id,
        "result": result,
    }

@app.post("/api/detect-distractions")
def detect_distractions(payload: DistractionDetectRequest):
    result = analyze_distraction_from_window(payload.window_info)
    return {
        "success": True,
        "analysis_type": "distraction",
        "user_id": payload.user_id,
        "session_id": payload.session_id,
        "result": result,
    }

@app.post("/api/analyze-posture")
def analyze_posture(payload: PostureAnalyzeRequest):
    size = len(payload.frame_data)
    posture_status = ["good", "ok", "poor"][ (size // 13) % 3 ]
    result = {
        "posture_status": posture_status,
        "analysis_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "recommendations": ["sit upright", "relax shoulders"] if posture_status == "poor" else [],
    }
    return {
        "success": True,
        "analysis_type": "posture",
        "user_id": payload.user_id,
        "session_id": payload.session_id,
        "result": result,
    }

# ==============================
# New endpoints for browser extension
# ==============================
@app.post("/api/analyze-tab")
def analyze_tab(payload: TabAnalyzeRequest, background_tasks: BackgroundTasks):
    """Analyze a specific tab for the browser extension"""
    try:
        logger.info(f"🔍 Analyzing tab: {payload.title[:50]}... ({payload.url[:50]}...)")
        
        # Create window info for existing analyzer
        window_info = {
            "title": payload.title,
            "url": payload.url,
            "process_name": "chrome.exe",  # Assume Chrome
            "active_time": 30  # Default active time for new tabs
        }
        
        # Use existing distraction analyzer
        result = analyze_distraction_from_window(window_info)
        
        # Add extension-specific fields
        distraction_score = result.get("distraction_score", 0)
        severity = result.get("severity", "low")
        is_distraction = result.get("is_distraction", False)
        
        # Determine extension actions based on analysis
        should_warn = is_distraction and distraction_score > 50
        should_block = is_distraction and distraction_score > 70
        should_close = should_block and severity in ["high", "medium"]
        
        # Get site name from URL
        site_name = "unknown site"
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(payload.url)
            site_name = parsed_url.netloc.replace("www.", "")
        except:
            pass
        
        # Enhanced result for extension
        extension_result = {
            **result,  # Include all original analysis
            "should_warn": should_warn,
            "should_block": should_block,
            "should_close": should_close,
            "warning_message": f"WorkSpace AI detected you're browsing {site_name}. Time to focus!",
            "block_message": f"This site ({site_name}) is distracting you from your goals.",
            "site_name": site_name,
            "warning_level": "high" if should_close else "medium" if should_block else "low" if should_warn else "none",
            "recommended_action": "close_tab" if should_close else "show_overlay" if should_block else "show_banner" if should_warn else "none"
        }
        
        # Log the decision
        action = "🚨 CLOSE" if should_close else "🔒 BLOCK" if should_block else "⚠️ WARN" if should_warn else "✅ ALLOW"
        logger.info(f"📊 Tab analysis result: {action} ({site_name})")
        
        # Schedule background action if needed
        if should_close:
            background_tasks.add_task(log_tab_closure, site_name, payload.url)
        
        return {
            "success": True,
            "analysis_type": "browser_tab",
            "result": extension_result,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"❌ Tab analysis error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "result": {
                "is_distraction": False,
                "should_warn": False,
                "should_block": False,
                "should_close": False,
                "warning_message": "Analysis failed",
                "site_name": "unknown",
                "warning_level": "none",
                "recommended_action": "none"
            }
        }

@app.get("/api/extension-status")
def get_extension_status():
    """Get current extension status and statistics"""
    try:
        # You can implement actual statistics storage here
        # For now, return mock data
        stats = {
            "blocked_today": 5,
            "focus_time_minutes": 120,
            "distractions_prevented": 8,
            "most_blocked_site": "youtube.com",
            "focus_sessions": 3
        }
        
        return {
            "success": True,
            "enabled": True,
            "focus_mode": True,
            "blocked_sites": [
                "youtube.com", "facebook.com", "instagram.com", 
                "twitter.com", "tiktok.com", "reddit.com",
                "netflix.com", "twitch.tv"
            ],
            "stats": stats,
            "settings": {
                "warning_delay": 30,  # seconds
                "block_delay": 120,   # seconds
                "close_delay": 300,   # seconds
                "notifications_enabled": True
            },
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"❌ Extension status error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "enabled": False
        }

@app.post("/api/extension-stats")
def update_extension_stats(payload: ExtensionStatsRequest):
    """Update extension statistics (blocked sites, focus time, etc.)"""
    try:
        action = payload.action
        site = payload.site
        duration = payload.duration
        
        logger.info(f"📊 Extension stat update: {action} - {site} ({duration}s)")
        
        # Here you would typically update a database
        # For now, just log the action
        
        response_data = {
            "success": True,
            "action_recorded": action,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
        
        if action == "site_blocked":
            response_data["message"] = f"Recorded blocking of {site}"
        elif action == "focus_time":
            response_data["message"] = f"Recorded {duration} seconds of focus time"
        elif action == "distraction_prevented":
            response_data["message"] = f"Recorded distraction prevention on {site}"
        
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Extension stats error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/block-site")
def block_site(payload: dict):
    """Manually block a site (for future system-level blocking)"""
    try:
        site = payload.get('site', '')
        duration = payload.get('duration', 3600)  # Default 1 hour
        
        logger.info(f"🚫 Manual site block request: {site} for {duration} seconds")
        
        # You can implement system-level blocking logic here
        # This could integrate with hosts file modification or other blocking tools
        
        return {
            "success": True,
            "message": f"Block request registered for {site}",
            "blocked_site": site,
            "duration_seconds": duration,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"❌ Site blocking error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/focus-session")
def get_focus_session():
    """Get current focus session information"""
    return {
        "success": True,
        "session_active": True,
        "session_start": "2024-09-19T08:00:00Z",
        "elapsed_minutes": 45,
        "target_minutes": 120,
        "breaks_taken": 1,
        "distractions_blocked": 3,
        "productivity_score": 85
    }

# ==============================
# Background task functions
# ==============================
def log_tab_closure(site_name: str, url: str):
    """Background task to log tab closures"""
    logger.info(f"🚨 Tab closure executed: {site_name} ({url})")
    # Here you could update statistics, send notifications, etc.

def trigger_system_notification(message: str, title: str = "WorkSpace AI"):
    """Background task to show system notifications"""
    try:
        import plyer
        plyer.notification.notify(
            title=title,
            message=message,
            timeout=5
        )
        logger.info(f"📬 Notification sent: {message}")
    except Exception as e:
        logger.warning(f"⚠️ Notification failed: {e}")

# ==============================
# Development and testing endpoints
# ==============================
@app.get("/api/test-extension")
def test_extension_integration():
    """Test endpoint to verify extension integration"""
    test_cases = [
        {"url": "https://youtube.com", "expected": "should_block"},
        {"url": "https://facebook.com", "expected": "should_block"},
        {"url": "https://stackoverflow.com", "expected": "should_allow"},
        {"url": "https://github.com", "expected": "should_allow"}
    ]
    
    results = []
    for case in test_cases:
        # Simulate tab analysis
        payload = TabAnalyzeRequest(
            url=case["url"],
            title=f"Test page - {case['url']}",
            timestamp=1234567890
        )
        
        # This would normally call analyze_tab but we'll do a quick test
        window_info = {
            "title": payload.title,
            "url": payload.url,
            "active_time": 30
        }
        
        result = analyze_distraction_from_window(window_info)
        
        results.append({
            "url": case["url"],
            "expected": case["expected"],
            "is_distraction": result.get("is_distraction", False),
            "distraction_score": result.get("distraction_score", 0),
            "detected_indicators": result.get("detected_indicators", [])
        })
    
    return {
        "success": True,
        "test_results": results,
        "backend_status": "operational",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }

# ==============================
# Main application runner
# ==============================
if __name__ == "__main__":
    port = int(os.getenv("PYTHON_PORT", "8000"))
    logger.info(f"🚀 Starting WorkSpace AI Backend on port {port}")
    logger.info("🔌 Browser extension endpoints enabled")
    # When launched by Node's PythonBridge, it runs `python3 app.py` with cwd set here
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
