#!/usr/bin/env python3
"""
Complete test script for YouTube distraction detection
"""
import requests
import base64
import time
import json
import os
from PIL import ImageGrab, ImageDraw, ImageFont
import io

def create_fake_youtube_screenshot():
    """Create a fake YouTube screenshot for testing"""
    # Create a fake screenshot with YouTube content
    img = ImageGrab.grab()
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to use a default font, fallback to default if not available
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    # Add YouTube-like text to the screenshot
    draw.text((100, 100), "YouTube - Funny Cat Videos", fill="red", font=font)
    draw.text((100, 150), "Subscribe • Like • Comment", fill="black", font=font)
    draw.text((100, 200), "🎵 Rick Astley - Never Gonna Give You Up", fill="black", font=font)
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    return base64.b64encode(img_data).decode('utf-8')

def capture_real_screenshot():
    """Capture real current screen as base64"""
    screenshot = ImageGrab.grab()
    buffer = io.BytesIO()
    screenshot.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    return base64.b64encode(img_data).decode('utf-8')

def test_backend_health():
    """Test if backend is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running!")
            print(f"   Health response: {response.json()}")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend connection failed: {e}")
        print("   Make sure to run: python app.py")
        return False

def test_screen_analysis(screenshot_b64, test_name):
    """Test screen analysis endpoint"""
    print(f"\n🧪 Testing: {test_name}")
    print("-" * 50)
    
    payload = {
        "screenshot_data": screenshot_b64,
        "user_id": "test_user_123",
        "session_id": "test_session_456"
    }
    
    try:
        print("📤 Sending request to /api/analyze-screen...")
        response = requests.post(
            "http://localhost:8000/api/analyze-screen",
            json=payload,
            timeout=30  # Increased timeout for OCR processing
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Analysis successful!")
            print(f"📊 Results:")
            print(f"   • Is Distraction: {result['result']['is_distraction']}")
            print(f"   • Distraction Score: {result['result']['distraction_score']}")
            print(f"   • Productivity Score: {result['result']['productivity_score']}")
            print(f"   • Content Type: {result['result']['content_type']}")
            
            if 'extracted_text' in result['result']:
                extracted = result['result']['extracted_text'][:100]
                print(f"   • Extracted Text: {extracted}...")
            
            if 'saved_screenshot' in result['result'] and result['result']['saved_screenshot']:
                print(f"   • Screenshot Saved: {result['result']['saved_screenshot']}")
            
            if result['result']['recommendations']:
                print(f"   • Recommendations: {result['result']['recommendations']}")
            
            return result['result']['is_distraction']
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False

def test_window_distraction():
    """Test window-based distraction detection"""
    print(f"\n🧪 Testing: Window Distraction Detection")
    print("-" * 50)
    
    # Test YouTube window
    window_info = {
        "title": "Funny Cat Videos Compilation 2024 - YouTube - Google Chrome",
        "process_name": "chrome.exe",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "active_time": 25
    }
    
    payload = {
        "window_info": window_info,
        "user_id": "test_user_123", 
        "session_id": "test_session_456"
    }
    
    try:
        print("📤 Sending request to /api/detect-distractions...")
        response = requests.post(
            "http://localhost:8000/api/detect-distractions",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Window analysis successful!")
            print(f"📊 Results:")
            print(json.dumps(result['result'], indent=2))
            return result['result']['is_distraction']
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    
    return False

def main():
    """Main test function"""
    print("🎯 WorkSpace AI Backend - YouTube Detection Test Suite")
    print("=" * 60)
    
    # Check environment
    screenshots_enabled = os.getenv('SAVE_SCREENSHOTS', 'false').lower() == 'true'
    print(f"📸 Screenshot saving: {'✅ ENABLED' if screenshots_enabled else '❌ DISABLED'}")
    if not screenshots_enabled:
        print("   💡 To enable: Set SAVE_SCREENSHOTS=true in .env file")
    
    # Test 1: Backend health
    if not test_backend_health():
        print("\n❌ Backend is not running. Please start it first:")
        print("   cd python-backend && python app.py")
        return
    
    # Test 2: Window distraction detection
    window_distraction = test_window_distraction()
    
    # Test 3: Fake YouTube screenshot
    print(f"\n🎬 Creating fake YouTube screenshot...")
    fake_youtube_screenshot = create_fake_youtube_screenshot()
    fake_result = test_screen_analysis(fake_youtube_screenshot, "Fake YouTube Screenshot")
    
    # Test 4: Real screenshot
    print(f"\n📱 MANUAL TEST:")
    print("1. Open YouTube in your browser")
    print("2. Play any funny video (like cat videos)")
    print("3. Make sure the video is visible on screen")
    input("4. Press ENTER when ready to capture your screen...")
    
    real_screenshot = capture_real_screenshot()
    real_result = test_screen_analysis(real_screenshot, "Real Screen Capture")
    
    # Test 5: Multiple captures (monitoring simulation)
    print(f"\n🔄 MONITORING SIMULATION:")
    print("Keep YouTube open - capturing every 3 seconds for 15 seconds...")
    
    distraction_count = 0
    total_captures = 5
    
    for i in range(total_captures):
        print(f"\n📸 Capture {i+1}/{total_captures}")
        screenshot = capture_real_screenshot()
        is_distraction = test_screen_analysis(screenshot, f"Monitoring Capture {i+1}")
        
        if is_distraction:
            distraction_count += 1
            print("🚨 DISTRACTION DETECTED!")
        
        if i < total_captures - 1:  # Don't wait after last capture
            time.sleep(3)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Backend Health: PASSED")
    print(f"✅ Window Detection: {'PASSED' if window_distraction else 'FAILED'}")
    print(f"✅ Fake YouTube: {'PASSED' if fake_result else 'FAILED'}")
    print(f"✅ Real Screenshot: {'PASSED' if real_result else 'FAILED'}")
    print(f"✅ Monitoring Test: {distraction_count}/{total_captures} distractions detected")
    
    if screenshots_enabled:
        screenshots_dir = os.path.join(os.getcwd(), 'screenshots')
        if os.path.exists(screenshots_dir):
            screenshot_count = len([f for f in os.listdir(screenshots_dir) if f.endswith('.png')])
            print(f"📸 Screenshots Saved: {screenshot_count} files in ./screenshots/")
    
    # Recommendations
    print(f"\n💡 NEXT STEPS:")
    if distraction_count > 0:
        print("✅ YouTube distraction detection is working!")
        print("   - The system successfully detected distracting content")
        print("   - Check the saved screenshots to verify accuracy")
    else:
        print("⚠️  No distractions detected. Try:")
        print("   - Make sure YouTube is open and visible")
        print("   - Check if OCR dependencies are installed (tesseract)")
        print("   - Review the extracted text in the console output")
    
    print(f"\n🔧 DEBUGGING:")
    print(f"   - Check console logs above for OCR extracted text")
    print(f"   - Screenshots saved in: ./screenshots/")
    print(f"   - Backend logs visible in terminal running 'python app.py'")

if __name__ == "__main__":
    main()
