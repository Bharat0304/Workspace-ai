from typing import Optional, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from ai_modules.analyzers import (
    analyze_screen_from_b64,
    analyze_focus_from_b64,
    analyze_distraction_from_window,
)


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


app = FastAPI(title="WorkSpace AI Python Backend", version="0.1.0")

# CORS: allow local dev frontend/backend
frontend_origin = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://localhost:3000", "http://localhost:5000", "http://localhost:5001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


if __name__ == "__main__":
    port = int(os.getenv("PYTHON_PORT", "8000"))
    # When launched by Node's PythonBridge, it runs `python3 app.py` with cwd set here
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)

