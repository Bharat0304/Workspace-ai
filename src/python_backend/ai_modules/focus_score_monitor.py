#!/usr/bin/env python3
"""
WorkSpace AI - OpenCV-Only Focus Score Monitor
Real-time focus monitoring using only OpenCV (no MediaPipe dependency)
Tracks: Eyes on screen, Phone usage, Upright shoulders
"""

import cv2
import numpy as np
import math
import time
import base64
from typing import Dict, Any, Tuple, List, Optional

class OpenCVFocusMonitor:
    """Focus monitoring using OpenCV built-in features only"""
    
    def __init__(self):
        """Initialize OpenCV models and tracking variables"""
        print("🎯 Initializing OpenCV Focus Monitor...")
        
        # Load OpenCV cascade classifiers
        try:
            # Face detection
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            # Eye detection
            self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            
            # Profile face (for side detection)
            self.profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
            
            # Upper body detection (for posture)
            self.body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_upperbody.xml')
            
            print("✅ OpenCV cascades loaded successfully")
            
        except Exception as e:
            print(f"❌ Error loading cascades: {e}")
            raise
        
        # Optional: DNN face detector (more robust than Haar)
        self.use_dnn = False
        self.dnn_net = None
        self.dnn_conf = float(os.getenv('FACE_DNN_CONF', '0.2')) if 'os' in globals() else 0.2
        self.dnn_only = False
        try:
            import os
            proto = os.getenv('FACE_DNN_PROTO', os.path.join(os.path.dirname(__file__), 'models', 'deploy.prototxt'))
            model = os.getenv('FACE_DNN_MODEL', os.path.join(os.path.dirname(__file__), 'models', 'res10_300x300_ssd_iter_140000.caffemodel'))
            if os.path.exists(proto) and os.path.exists(model):
                self.dnn_net = cv2.dnn.readNetFromCaffe(proto, model)
                self.use_dnn = True
                self.dnn_only = os.getenv('FACE_DNN_ONLY', 'false').lower() == 'true'
                print("✅ DNN face detector loaded (Res10)")
            else:
                print("ℹ️ DNN face model files not found - using Haar cascades")
        except Exception as e:
            print(f"⚠️ Failed to load DNN face detector: {e}")
        
        # Focus tracking variables
        self.focus_history = []
        self.session_start = time.time()
        self.last_analysis = {}
        self.frame_count = 0
        
        # Calibration data
        self.baseline_face_size = None
        self.baseline_face_position = None
        
        print("✅ OpenCV Focus Monitor initialized")

    def detect_face_and_eyes(self, frame: np.ndarray) -> Dict[str, Any]:
        """Detect face and eyes using OpenCV cascades with robust preprocessing"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Improve contrast for low-light/overexposed scenes
            try:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                gray = clahe.apply(gray)
            except Exception:
                gray = cv2.equalizeHist(gray)
            h, w = frame.shape[:2]
            
            # Detect faces (prefer DNN if available)
            faces = []
            if self.use_dnn and self.dnn_net is not None:
                try:
                    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0), False, False)
                    self.dnn_net.setInput(blob)
                    detections = self.dnn_net.forward()
                    for i in range(detections.shape[2]):
                        confidence = detections[0, 0, i, 2]
                        if confidence > self.dnn_conf:
                            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                            (x1, y1, x2, y2) = box.astype("int")
                            x = max(0, x1)
                            y = max(0, y1)
                            fw = max(0, x2 - x1)
                            fh = max(0, y2 - y1)
                            if fw > 40 and fh > 40:
                                faces.append([x, y, fw, fh])
                except Exception as e:
                    print(f"⚠️ DNN detection failed, falling back to Haar: {e}")
                    faces = []

            if len(faces) == 0 and not self.dnn_only:
                # Haar cascade fallback
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.05, minNeighbors=2, minSize=(40, 40)
                )
            # Try alternate frontal cascades if none found
            if len(faces) == 0 and not self.dnn_only:
                try:
                    alt1 = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')
                    faces = alt1.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=2, minSize=(40, 40))
                except Exception:
                    pass
            if len(faces) == 0 and not self.dnn_only:
                try:
                    alt2 = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml')
                    faces = alt2.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=2, minSize=(40, 40))
                except Exception:
                    pass
            
            if len(faces) == 0 and not self.dnn_only:
                # Try profile detection if no frontal face found
                profiles = self.profile_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
                )
                
                if len(profiles) > 0:
                    return {
                        "face_detected": True,
                        "face_position": "profile",
                        "looking_at_screen": False,
                        "eye_gaze": "side",
                        "face_confidence": 0.6,
                        "face_rect": profiles[0].tolist(),
                        "eyes_detected": 0,
                        "face_center": [profiles[0][0] + profiles[0][2]//2, profiles[0][1] + profiles[0][3]//2]
                    }
                else:
                    return {
                        "face_detected": False,
                        "looking_at_screen": False,
                        "eye_gaze": "unknown",
                        "face_confidence": 0.0
                    }
            
            # Use the largest/most confident face
            face = max(faces, key=lambda x: x[2] * x[3])  # Largest face by area
            x, y, fw, fh = face
            
            face_center = [x + fw//2, y + fh//2]
            face_roi_gray = gray[y:y+fh, x:x+fw]
            
            # Detect eyes within face region
            eyes = self.eye_cascade.detectMultiScale(
                face_roi_gray, scaleFactor=1.05, minNeighbors=2, minSize=(16, 16)
            )
            
            # Analyze face position for screen focus
            screen_center_x = w // 2
            screen_center_y = h // 2
            
            # Calculate face deviation from center
            face_offset_x = face_center[0] - screen_center_x
            face_offset_y = face_center[1] - screen_center_y
            
            # Determine if looking at screen based on face position
            # Good screen position: face centered, not too close/far
            face_size = fw * fh
            
            # Normalize face size for distance estimation
            if self.baseline_face_size is None:
                self.baseline_face_size = face_size
            
            size_ratio = face_size / self.baseline_face_size if self.baseline_face_size > 0 else 1.0
            
            # Screen focus criteria
            is_centered_x = abs(face_offset_x) < w * 0.2  # Within 20% of center
            is_centered_y = abs(face_offset_y) < h * 0.15  # Within 15% of center
            is_good_distance = 0.7 < size_ratio < 1.5     # Not too close/far
            # Some cameras/angles may detect only one eye - be lenient
            has_both_eyes = len(eyes) >= 1
            
            # Calculate gaze direction
            gaze_direction = "center"
            if abs(face_offset_x) > abs(face_offset_y):
                gaze_direction = "right" if face_offset_x > 30 else "left" if face_offset_x < -30 else "center"
            else:
                gaze_direction = "down" if face_offset_y > 20 else "up" if face_offset_y < -20 else "center"
            
            # Overall screen focus assessment
            looking_at_screen = is_centered_x and is_centered_y and is_good_distance and has_both_eyes
            
            # Calculate confidence
            confidence_factors = [
                is_centered_x, is_centered_y, is_good_distance, has_both_eyes
            ]
            face_confidence = sum(confidence_factors) / len(confidence_factors)
            
            # Eye analysis
            eye_analysis = self.analyze_eye_positions(eyes, face_roi_gray, (fw, fh))
            
            return {
                "face_detected": True,
                "face_position": "frontal",
                "looking_at_screen": looking_at_screen,
                "eye_gaze": gaze_direction,
                "face_confidence": round(face_confidence, 2),
                "face_rect": face.tolist(),
                "face_center": face_center,
                "face_size": face_size,
                "eyes_detected": len(eyes),
                "eye_analysis": eye_analysis,
                "positioning": {
                    "centered_x": is_centered_x,
                    "centered_y": is_centered_y,
                    "good_distance": is_good_distance,
                    "both_eyes_visible": has_both_eyes
                }
            }
            
        except Exception as e:
            print(f"❌ Face detection error: {e}")
            return {
                "face_detected": False,
                "looking_at_screen": False,
                "eye_gaze": "error",
                "face_confidence": 0.0
            }

    def analyze_eye_positions(self, eyes, face_roi_gray, face_size: Tuple[int, int]) -> Dict[str, Any]:
        """Analyze eye positions for blink detection and gaze estimation"""
        try:
            fw, fh = face_size
            
            if len(eyes) < 2:
                return {
                    "blink_detected": False,
                    "eye_openness": 0.0,
                    "eye_symmetry": 0.0,
                    "gaze_stability": 0.0
                }
            
            # Sort eyes by x position (left to right)
            eyes = sorted(eyes, key=lambda e: e[0])
            left_eye, right_eye = eyes[0], eyes[1] if len(eyes) > 1 else eyes[0]
            
            # Calculate eye properties
            left_eye_area = left_eye[2] * left_eye[3]
            right_eye_area = right_eye[2] * right_eye[3]
            
            # Eye openness (larger area = more open)
            avg_eye_area = (left_eye_area + right_eye_area) / 2
            relative_eye_size = avg_eye_area / (fw * fh) * 100  # Percentage of face
            
            # Normal eye size is about 2-4% of face area
            eye_openness = min(1.0, relative_eye_size / 3.0)
            
            # Blink detection (very small eye area)
            blink_detected = relative_eye_size < 1.0
            
            # Eye symmetry (similar sizes indicate good frontal view)
            size_diff = abs(left_eye_area - right_eye_area)
            max_eye_area = max(left_eye_area, right_eye_area)
            eye_symmetry = 1.0 - (size_diff / max_eye_area) if max_eye_area > 0 else 0.0
            
            return {
                "blink_detected": blink_detected,
                "eye_openness": round(eye_openness, 2),
                "eye_symmetry": round(eye_symmetry, 2),
                "gaze_stability": round(eye_symmetry * eye_openness, 2),
                "left_eye_area": left_eye_area,
                "right_eye_area": right_eye_area,
                "relative_eye_size": round(relative_eye_size, 2)
            }
            
        except Exception as e:
            print(f"❌ Eye analysis error: {e}")
            return {"blink_detected": False, "eye_openness": 0.0}

    def analyze_posture(self, frame: np.ndarray, face_data: Dict) -> Dict[str, Any]:
        """Analyze body posture using upper body detection and face position"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = frame.shape[:2]
            
            # Detect upper body
            bodies = self.body_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(100, 100)
            )
            
            posture_score = 50  # Default score
            posture_indicators = {}
            
            if len(bodies) > 0 and face_data.get("face_detected"):
                # Use largest detected body
                body = max(bodies, key=lambda x: x[2] * x[3])
                bx, by, bw, bh = body
                
                # Get face position
                face_center = face_data.get("face_center", [w//2, h//2])
                face_rect = face_data.get("face_rect", [0, 0, 100, 100])
                fx, fy, fw, fh = face_rect
                
                # 1. Head-to-body alignment
                body_center_x = bx + bw//2
                head_body_alignment = abs(face_center[0] - body_center_x)
                is_aligned = head_body_alignment < bw * 0.2  # Within 20% of body width
                
                # 2. Head position relative to body (should be in upper portion)
                head_body_ratio = (face_center[1] - by) / bh if bh > 0 else 0.5
                is_head_positioned_well = 0.1 < head_body_ratio < 0.4  # Head in upper body area
                
                # 3. Body width (indicates facing camera)
                expected_body_width = w * 0.25  # Expected body width
                body_width_ratio = bw / expected_body_width
                is_facing_camera = 0.8 < body_width_ratio < 1.5
                
                # 4. Body straightness (vertical alignment)
                body_aspect_ratio = bh / bw if bw > 0 else 1.0
                is_upright = body_aspect_ratio > 1.2  # Taller than wide
                
                # Calculate posture score
                posture_factors = [
                    is_aligned, is_head_positioned_well, is_facing_camera, is_upright
                ]
                posture_score = 25 + (sum(posture_factors) / len(posture_factors)) * 75
                
                posture_indicators = {
                    "body_detected": True,
                    "head_body_aligned": is_aligned,
                    "head_positioned_well": is_head_positioned_well,
                    "facing_camera": is_facing_camera,
                    "upright_posture": is_upright,
                    "body_rect": body.tolist(),
                    "alignment_offset": head_body_alignment,
                    "body_width_ratio": round(body_width_ratio, 2)
                }
                
            else:
                # No body detected, use face position for basic posture assessment
                if face_data.get("face_detected"):
                    face_rect = face_data.get("face_rect", [0, 0, 100, 100])
                    fx, fy, fw, fh = face_rect
                    
                    # Basic posture from face position
                    face_center_x = fx + fw//2
                    face_y_position = fy + fh//2
                    
                    # Face should be in upper-middle portion of screen
                    is_centered = abs(face_center_x - w//2) < w * 0.15
                    is_good_height = 0.2 < (face_y_position / h) < 0.6
                    
                    posture_score = 40 if is_centered and is_good_height else 25
                    
                    posture_indicators = {
                        "body_detected": False,
                        "face_centered": is_centered,
                        "good_face_height": is_good_height,
                        "estimated_from_face": True
                    }
                else:
                    posture_indicators = {"body_detected": False, "face_detected": False}
            
            # Determine posture level
            if posture_score >= 80:
                posture_level = "excellent"
            elif posture_score >= 65:
                posture_level = "good"
            elif posture_score >= 50:
                posture_level = "fair"
            else:
                posture_level = "poor"
            
            # Generate recommendations
            recommendations = []
            if not posture_indicators.get("head_body_aligned", True):
                recommendations.append("Center your head above your body")
            if not posture_indicators.get("upright_posture", True):
                recommendations.append("Sit up straight")
            if not posture_indicators.get("facing_camera", True):
                recommendations.append("Face the camera directly")
            if not recommendations:
                recommendations.append("Good posture!")
            
            return {
                "posture_score": round(posture_score, 1),
                "posture_level": posture_level,
                "indicators": posture_indicators,
                "recommendations": recommendations
            }
            
        except Exception as e:
            print(f"❌ Posture analysis error: {e}")
            return {
                "posture_score": 30.0,
                "posture_level": "unknown",
                "recommendations": ["Unable to analyze posture"]
            }

    def detect_phone_usage(self, frame: np.ndarray, face_data: Dict) -> Dict[str, Any]:
        """Detect potential phone usage using motion and face position analysis"""
        try:
            h, w = frame.shape[:2]
            
            # Basic phone usage indicators using available data
            phone_confidence = 0.0
            phone_indicators = []
            
            if face_data.get("face_detected"):
                face_center = face_data.get("face_center", [w//2, h//2])
                face_rect = face_data.get("face_rect", [0, 0, 100, 100])
                fx, fy, fw, fh = face_rect
                
                # 1. Face too low (looking down at device)
                face_y_ratio = face_center[1] / h
                if face_y_ratio > 0.6:  # Face in lower 40% of image
                    phone_confidence += 0.3
                    phone_indicators.append("looking_down")
                
                # 2. Face too close (holding device close)
                face_size = fw * fh
                if self.baseline_face_size and face_size > self.baseline_face_size * 1.3:
                    phone_confidence += 0.2
                    phone_indicators.append("too_close")
                
                # 3. Face tilted/angled (holding device at angle)
                eye_analysis = face_data.get("eye_analysis", {})
                eye_symmetry = eye_analysis.get("eye_symmetry", 1.0)
                if eye_symmetry < 0.7:  # Eyes not symmetrical = tilted face
                    phone_confidence += 0.2
                    phone_indicators.append("tilted_face")
                
                # 4. Profile face detected (looking sideways)
                if face_data.get("face_position") == "profile":
                    phone_confidence += 0.4
                    phone_indicators.append("profile_view")
                
                # 5. Poor eye gaze direction
                eye_gaze = face_data.get("eye_gaze", "center")
                if eye_gaze in ["down", "side"]:
                    phone_confidence += 0.1
                    phone_indicators.append("poor_gaze")
                
            else:
                # No face detected might indicate phone covering face
                phone_confidence = 0.2
                phone_indicators.append("no_face_detected")
            
            # Normalize confidence
            phone_confidence = min(phone_confidence, 1.0)
            
            # Determine phone usage
            phone_detected = phone_confidence > 0.4
            
            # Risk assessment
            if phone_confidence > 0.7:
                risk_level = "high"
                warning = "🚨 High probability of phone usage detected!"
            elif phone_confidence > 0.4:
                risk_level = "medium"  
                warning = "⚠️ Possible phone usage detected"
            else:
                risk_level = "low"
                warning = "✅ No phone usage detected"
            
            return {
                "phone_detected": phone_detected,
                "phone_confidence": round(phone_confidence, 2),
                "risk_level": risk_level,
                "warning_message": warning,
                "indicators": phone_indicators,
                "recommendation": "Put phone away and focus on screen" if phone_detected else "Great! Stay focused"
            }
            
        except Exception as e:
            print(f"❌ Phone detection error: {e}")
            return {
                "phone_detected": False,
                "phone_confidence": 0.0,
                "risk_level": "low",
                "indicators": []
            }

    def calculate_focus_score(self, gaze_data: Dict, posture_data: Dict, phone_data: Dict) -> Dict[str, Any]:
        """Calculate comprehensive focus score"""
        try:
            # Component weights
            GAZE_WEIGHT = 0.45      # 45% - most important
            POSTURE_WEIGHT = 0.35   # 35% - important for health
            PHONE_PENALTY = 0.20    # 20% - penalty for distraction
            
            # Calculate component scores
            
            # 1. Gaze score (0-45 points)
            gaze_score = 0
            if gaze_data.get("face_detected", False):
                if gaze_data.get("looking_at_screen", False):
                    confidence = gaze_data.get("face_confidence", 0.5)
                    gaze_score = GAZE_WEIGHT * 100 * confidence
                else:
                    gaze_score = 10  # Some points for face detected but not looking
            
            # 2. Posture score (0-35 points)  
            posture_raw_score = posture_data.get("posture_score", 50)
            posture_score = (posture_raw_score / 100) * POSTURE_WEIGHT * 100
            
            # 3. Phone penalty (0-20 points deducted)
            phone_confidence = phone_data.get("phone_confidence", 0)
            phone_penalty = phone_confidence * PHONE_PENALTY * 100
            
            # Calculate total score
            total_score = gaze_score + posture_score - phone_penalty
            total_score = max(0, min(100, total_score))  # Clamp to 0-100
            
            # Determine focus level
            if total_score >= 85:
                focus_level = "excellent"
                focus_color = "green"
            elif total_score >= 70:
                focus_level = "good"  
                focus_color = "lightgreen"
            elif total_score >= 50:
                focus_level = "fair"
                focus_color = "yellow"
            elif total_score >= 30:
                focus_level = "poor"
                focus_color = "orange"
            else:
                focus_level = "critical"
                focus_color = "red"
            
            # Generate comprehensive recommendations
            recommendations = []
            
            if gaze_score < 25:
                recommendations.append("Look directly at your screen")
            if posture_score < 20:
                recommendations.extend(posture_data.get("recommendations", []))
            if phone_penalty > 10:
                recommendations.append(phone_data.get("recommendation", "Avoid phone usage"))
                
            if not recommendations:
                recommendations.append("Excellent focus! Keep it up!")
            
            # Track focus history
            current_time = time.time()
            self.focus_history.append({
                "timestamp": current_time,
                "score": total_score,
                "components": {
                    "gaze": gaze_score,
                    "posture": posture_score,
                    "phone_penalty": phone_penalty
                }
            })
            
            # Keep only last 5 minutes
            cutoff_time = current_time - 300
            self.focus_history = [h for h in self.focus_history if h["timestamp"] > cutoff_time]
            
            return {
                "overall_focus_score": round(total_score, 1),
                "focus_level": focus_level,
                "focus_color": focus_color,
                "component_scores": {
                    "gaze_score": round(gaze_score, 1),
                    "posture_score": round(posture_score, 1),
                    "phone_penalty": round(phone_penalty, 1)
                },
                "recommendations": recommendations[:3],  # Limit to top 3
                "session_average": round(np.mean([h["score"] for h in self.focus_history]), 1) if self.focus_history else total_score
            }
            
        except Exception as e:
            print(f"❌ Focus calculation error: {e}")
            return {
                "overall_focus_score": 0.0,
                "focus_level": "error",
                "recommendations": ["Error calculating focus score"]
            }

    def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Main analysis function - analyze single frame for focus metrics"""
        try:
            self.frame_count += 1
            analysis_timestamp = time.time()
            
            # 1. Detect face and eyes
            gaze_data = self.detect_face_and_eyes(frame)
            
            # 2. Analyze posture
            posture_data = self.analyze_posture(frame, gaze_data)
            
            # 3. Detect phone usage
            phone_data = self.detect_phone_usage(frame, gaze_data)
            
            # 4. Calculate overall focus score
            focus_metrics = self.calculate_focus_score(gaze_data, posture_data, phone_data)
            
            # 5. Generate alerts
            alerts = []
            if not gaze_data.get("looking_at_screen", True):
                alerts.append("Eyes not focused on screen")
            if posture_data.get("posture_score", 100) < 50:
                alerts.append("Poor posture detected")
            if phone_data.get("phone_detected", False):
                alerts.append("Possible phone usage")
            
            # Compile comprehensive result
            result = {
                # Timestamps and session info
                "timestamp": analysis_timestamp,
                "session_duration_minutes": round((analysis_timestamp - self.session_start) / 60, 1),
                "frame_count": self.frame_count,
                
                # Core focus metrics
                "focus_score": focus_metrics["overall_focus_score"],
                "focus_level": focus_metrics["focus_level"],
                "focus_color": focus_metrics["focus_color"],
                
                # Component analysis
                "gaze_analysis": gaze_data,
                "posture_analysis": posture_data,
                "phone_analysis": phone_data,
                
                # Scoring breakdown
                "component_scores": focus_metrics["component_scores"],
                
                # Actionable insights
                "recommendations": focus_metrics["recommendations"],
                "alerts": alerts,
                
                # Session statistics
                "session_average_focus": focus_metrics["session_average"],
                
                # Detection quality
                "analysis_quality": "good" if gaze_data.get("face_detected") else "limited",
                
                # Simplified API compatibility
                "eye_gaze": gaze_data.get("eye_gaze", "unknown"),
                "looking_at_screen": gaze_data.get("looking_at_screen", False),
                "face_detected": gaze_data.get("face_detected", False),
                "posture_score": posture_data.get("posture_score", 0),
                "phone_detected": phone_data.get("phone_detected", False)
            }
            
            self.last_analysis = result
            return result
            
        except Exception as e:
            print(f"❌ Frame analysis error: {e}")
            return {
                "error": str(e),
                "timestamp": time.time(),
                "focus_score": 0,
                "focus_level": "error",
                "face_detected": False,
                "recommendations": ["Error analyzing frame - check camera"]
            }

    def draw_analysis_overlay(self, frame: np.ndarray, analysis_result: Dict[str, Any]) -> np.ndarray:
        """Draw focus analysis overlay on frame"""
        try:
            overlay = frame.copy()
            h, w = frame.shape[:2]
            
            # Get analysis data
            focus_score = analysis_result.get("focus_score", 0)
            focus_level = analysis_result.get("focus_level", "unknown")
            gaze_data = analysis_result.get("gaze_analysis", {})
            
            # Color mapping
            colors = {
                "excellent": (0, 255, 0),
                "good": (0, 255, 127),
                "fair": (0, 255, 255),
                "poor": (0, 127, 255), 
                "critical": (0, 0, 255),
                "error": (128, 128, 128)
            }
            color = colors.get(focus_level, (128, 128, 128))
            
            # Main focus display
            cv2.rectangle(overlay, (10, 10), (380, 140), (0, 0, 0), -1)
            cv2.rectangle(overlay, (10, 10), (380, 140), color, 2)
            
            # Focus score
            cv2.putText(overlay, f"FOCUS SCORE: {focus_score:.1f}%", 
                       (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
            cv2.putText(overlay, f"Level: {focus_level.upper()}", 
                       (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Component status
            looking_status = "👁️ ON SCREEN" if gaze_data.get("looking_at_screen") else "👁️ LOOKING AWAY"
            cv2.putText(overlay, looking_status, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                       (0, 255, 0) if gaze_data.get("looking_at_screen") else (0, 0, 255), 2)
            
            # Phone warning
            phone_data = analysis_result.get("phone_analysis", {})
            if phone_data.get("phone_detected"):
                cv2.putText(overlay, "📱 PHONE DETECTED!", (20, 130), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # Draw face rectangle if detected
            if gaze_data.get("face_detected") and "face_rect" in gaze_data:
                fx, fy, fw, fh = gaze_data["face_rect"]
                cv2.rectangle(overlay, (fx, fy), (fx+fw, fy+fh), color, 2)
                cv2.putText(overlay, f"Focus: {gaze_data.get('face_confidence', 0):.1f}", 
                           (fx, fy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Component scores (bottom right)
            comp_scores = analysis_result.get("component_scores", {})
            y_start = h - 100
            cv2.rectangle(overlay, (w-200, y_start-20), (w-10, h-10), (0, 0, 0), -1)
            cv2.putText(overlay, "COMPONENTS:", (w-190, y_start), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(overlay, f"Gaze: {comp_scores.get('gaze_score', 0):.1f}", 
                       (w-190, y_start+20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(overlay, f"Posture: {comp_scores.get('posture_score', 0):.1f}", 
                       (w-190, y_start+40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(overlay, f"Phone: -{comp_scores.get('phone_penalty', 0):.1f}", 
                       (w-190, y_start+60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            
            return overlay
            
        except Exception as e:
            print(f"❌ Overlay error: {e}")
            return frame

# Integration function for your backend API
def analyze_focus_from_b64(frame_b64: str) -> Dict[str, Any]:
    """
    Integration function for WorkSpace AI backend API
    Analyzes base64 encoded frame and returns focus metrics
    """
    try:
        # Decode base64 image
        img_bytes = base64.b64decode(frame_b64)
        img_array = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {
                "error": "Failed to decode frame",
                "focus_score": 0,
                "focus_level": "error",
                "face_detected": False,
                "looking_at_screen": False
            }
        
        # Initialize monitor if not exists (singleton pattern)
        if not hasattr(analyze_focus_from_b64, 'monitor'):
            analyze_focus_from_b64.monitor = OpenCVFocusMonitor()
        
        # Analyze frame
        result = analyze_focus_from_b64.monitor.analyze_frame(frame)
        
        # Generate small annotated overlay for debugging in UI
        try:
            overlay = analyze_focus_from_b64.monitor.draw_analysis_overlay(frame, result)
            h, w = overlay.shape[:2]
            target_w = 320
            scale = target_w / max(1, w)
            new_w, new_h = target_w, max(1, int(h * scale))
            overlay_small = cv2.resize(overlay, (new_w, new_h))
            ok, buf = cv2.imencode('.jpg', overlay_small, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            overlay_b64 = base64.b64encode(buf.tobytes()).decode('utf-8') if ok else None
        except Exception as e:
            print(f"⚠️ Overlay encode failed: {e}")
            overlay_b64 = None
        
        # Format for API compatibility
        api_result = {
            # Main metrics
            "focus_score": result.get("focus_score", 0),
            "focus_level": result.get("focus_level", "unknown"),
            "eye_gaze": result.get("eye_gaze", "unknown"),
            "looking_at_screen": result.get("looking_at_screen", False),
            "face_detected": result.get("face_detected", False),
            
            # Additional metrics
            "posture_score": result.get("posture_score", 0),
            "phone_detected": result.get("phone_detected", False),
            "phone_confidence": result.get("phone_analysis", {}).get("phone_confidence", 0),
            
            # Guidance
            "recommendations": result.get("recommendations", []),
            "alerts": result.get("alerts", []),
            
            # Session data
            "session_duration_minutes": result.get("session_duration_minutes", 0),
            "session_average_focus": result.get("session_average_focus", result.get("focus_score", 0)),
            "analysis_timestamp": result.get("timestamp"),
            
            # Full analysis for advanced usage
            "detailed_analysis": result,
            "overlay_b64": overlay_b64
        }
        
        # Sanitize to JSON-safe types (convert numpy types/ndarrays/tuples)
        def _json_safe(obj):
            try:
                import numpy as _np
            except Exception:
                _np = None
            if _np is not None:
                if isinstance(obj, _np.bool_):
                    return bool(obj)
                if isinstance(obj, (_np.integer,)):
                    return int(obj)
                if isinstance(obj, (_np.floating,)):
                    return float(obj)
                if isinstance(obj, _np.ndarray):
                    return obj.tolist()
            if isinstance(obj, dict):
                return {str(k): _json_safe(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple, set)):
                return [_json_safe(v) for v in obj]
            return obj

        return _json_safe(api_result)
        
    except Exception as e:
        print(f"❌ Focus analysis API error: {e}")
        return {
            "error": str(e),
            "focus_score": 0,
            "focus_level": "error",
            "eye_gaze": "unknown",
            "looking_at_screen": False,
            "face_detected": False,
            "recommendations": ["Error analyzing focus - check camera and lighting"],
            "alerts": ["Analysis failed"]
        }

# Test function
if __name__ == "__main__":
    """Test the OpenCV focus monitor with live webcam"""
    print("🎯 WorkSpace AI - OpenCV Focus Monitor Test")
    print("Controls: 'q' to quit, 's' to save screenshot")
    
    # Initialize monitor
    monitor = OpenCVFocusMonitor()
    
    # Open webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera")
        exit(1)
    
    print("✅ Camera opened - starting focus monitoring...")
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Analyze every 5th frame for performance
        if frame_count % 5 == 0:
            analysis = monitor.analyze_frame(frame)
            display_frame = monitor.draw_analysis_overlay(frame, analysis)
            
            # Print focus score periodically
            if frame_count % 50 == 0:
                focus_score = analysis.get("focus_score", 0)
                focus_level = analysis.get("focus_level", "unknown")
                print(f"📊 Current Focus: {focus_score:.1f}% ({focus_level})")
        else:
            display_frame = frame
        
        cv2.imshow('WorkSpace AI - OpenCV Focus Monitor', display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            timestamp = int(time.time())
            filename = f'opencv_focus_{timestamp}.jpg'
            cv2.imwrite(filename, display_frame)
            print(f"💾 Screenshot saved: {filename}")
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Session summary
    if monitor.focus_history:
        scores = [h["score"] for h in monitor.focus_history]
        session_time = (time.time() - monitor.session_start) / 60
        print(f"\n📈 Session Summary:")
        print(f"   Duration: {session_time:.1f} minutes")
        print(f"   Average Focus: {np.mean(scores):.1f}%")
        print(f"   Peak Focus: {max(scores):.1f}%")
        print(f"   Total Measurements: {len(scores)}")
    
    print("👋 Focus monitoring complete!")
