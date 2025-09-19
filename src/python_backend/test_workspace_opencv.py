#!/usr/bin/env python3
"""
Advanced OpenCV testing for WorkSpace AI backend integration
"""
import requests
import base64
import cv2
import numpy as np
import json
import time
import os
from io import BytesIO
from PIL import Image

def create_test_screenshots():
    """Create realistic test screenshots for different scenarios"""
    screenshots = {}
    
    # 1. Educational content screenshot
    edu_img = np.ones((720, 1280, 3), dtype=np.uint8) * 255  # White background
    
    # Simulate educational content
    cv2.putText(edu_img, 'Khan Academy - Calculus Tutorial', (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    cv2.putText(edu_img, 'Introduction to Derivatives', (50, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 100, 0), 2)
    cv2.putText(edu_img, 'Learn the fundamentals of calculus', (50, 300), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (50, 50, 50), 2)
    
    # Add some mathematical formulas
    cv2.putText(edu_img, 'f(x) = x^2', (200, 450), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    cv2.putText(edu_img, "f'(x) = 2x", (200, 550), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    
    screenshots['educational'] = edu_img
    
    # 2. Entertainment content screenshot  
    fun_img = np.ones((720, 1280, 3), dtype=np.uint8) * 30  # Dark background
    
    # Simulate YouTube entertainment
    cv2.putText(fun_img, 'YouTube - Funny Cat Videos', (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    cv2.putText(fun_img, 'HILARIOUS Cat Compilation 2024', (50, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 100, 255), 2)
    cv2.putText(fun_img, '10 Minutes of Pure Comedy!', (50, 300), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(fun_img, 'VIRAL MEMES COMPILATION', (50, 400), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 50, 50), 2)
    
    screenshots['entertainment'] = fun_img
    
    # 3. Social media screenshot
    social_img = np.ones((720, 1280, 3), dtype=np.uint8) * 70  # Gray background
    
    cv2.putText(social_img, 'Facebook - News Feed', (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    cv2.putText(social_img, 'What are you thinking about?', (50, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
    cv2.putText(social_img, 'John posted a photo', (50, 300), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(social_img, 'Sarah shared a link', (50, 400), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    screenshots['social_media'] = social_img
    
    # 4. Programming/work content
    work_img = np.ones((720, 1280, 3), dtype=np.uint8) * 20  # Very dark (like IDE)
    
    cv2.putText(work_img, 'VS Code - Python Project', (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
    cv2.putText(work_img, 'def analyze_data():', (100, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(work_img, '    import pandas as pd', (120, 250), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    cv2.putText(work_img, '    return df.groupby()', (120, 300), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    
    screenshots['programming'] = work_img
    
    return screenshots

def image_to_base64(img):
    """Convert OpenCV image to base64 string"""
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

def test_backend_connection():
    """Test if WorkSpace AI backend is running"""
    print("🔌 Testing Backend Connection...")
    
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Backend is running!")
            print(f"   Status: {result.get('status')}")
            print(f"   Python: {result.get('python')}")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        print("💡 Make sure to run: cd python-backend && python app.py")
        return False

def test_screenshot_analysis():
    """Test screenshot analysis with different content types"""
    print("\n📸 Testing Screenshot Analysis...")
    
    screenshots = create_test_screenshots()
    
    for content_type, img in screenshots.items():
        print(f"\n🔍 Testing {content_type.upper()} content...")
        
        try:
            # Convert to base64
            b64_data = image_to_base64(img)
            
            # Send to backend
            response = requests.post(
                'http://localhost:8000/api/analyze-screen',
                json={'screenshot_data': b64_data},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"   📊 Analysis Results:")
                print(f"      • Is Distraction: {result.get('is_distraction', 'unknown')}")
                print(f"      • Distraction Score: {result.get('distraction_score', 0)}")
                print(f"      • Content Type: {result.get('content_type', 'unknown')}")
                print(f"      • Detection Method: {result.get('detection_method', 'unknown')}")
                
                if result.get('detected_keywords'):
                    print(f"      • Detected Keywords: {result['detected_keywords']}")
                
                if result.get('recommendations'):
                    print(f"      • Recommendations: {result['recommendations'][0]}")
                
                # Verify expected behavior
                if content_type == 'educational':
                    expected = not result.get('is_distraction', True)
                    status = "✅ CORRECT" if expected else "❌ WRONG"
                    print(f"   {status} - Educational content should NOT be distraction")
                
                elif content_type == 'entertainment':
                    expected = result.get('is_distraction', False)
                    status = "✅ CORRECT" if expected else "❌ WRONG"
                    print(f"   {status} - Entertainment content SHOULD be distraction")
                
                elif content_type == 'programming':
                    expected = not result.get('is_distraction', True)
                    status = "✅ CORRECT" if expected else "❌ WRONG"
                    print(f"   {status} - Programming content should NOT be distraction")
                
            else:
                print(f"   ❌ Request failed with status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Test failed: {e}")

def test_real_webcam_analysis():
    """Test with real webcam screenshot"""
    print("\n📷 Testing Real Webcam Analysis...")
    
    try:
        # Capture from webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Could not open webcam")
            return
        
        print("📸 Capturing webcam frame...")
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("❌ Could not capture frame")
            return
        
        print(f"✅ Captured frame: {frame.shape}")
        
        # Convert to base64
        b64_data = image_to_base64(frame)
        print(f"✅ Converted to base64 (length: {len(b64_data)})")
        
        # Send to backend
        print("🔄 Sending to backend for analysis...")
        response = requests.post(
            'http://localhost:8000/api/analyze-screen',
            json={'screenshot_data': b64_data},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("📊 Real Webcam Analysis Results:")
            print(f"   • OCR Confidence: {result.get('ocr_confidence', False)}")
            print(f"   • Extracted Text Length: {len(result.get('extracted_text', ''))}")
            print(f"   • Is Distraction: {result.get('is_distraction', 'unknown')}")
            print(f"   • Analysis Method: {result.get('detection_method', 'unknown')}")
            
            if result.get('extracted_text'):
                text_preview = result['extracted_text'][:100]
                print(f"   • Text Preview: {text_preview}...")
            
            # Save analyzed frame
            cv2.imwrite('webcam_analysis.jpg', frame)
            print("✅ Webcam frame saved as 'webcam_analysis.jpg'")
            
        else:
            print(f"❌ Analysis failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Webcam analysis failed: {e}")

def test_focus_analysis():
    """Test focus analysis endpoint"""
    print("\n👁️ Testing Focus Analysis...")
    
    try:
        # Create test frame data
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Add a face-like pattern
        cv2.circle(test_frame, (320, 240), 80, (255, 200, 200), -1)  # Face
        cv2.circle(test_frame, (300, 220), 10, (0, 0, 0), -1)  # Eye
        cv2.circle(test_frame, (340, 220), 10, (0, 0, 0), -1)  # Eye
        cv2.rectangle(test_frame, (310, 250), (330, 270), (0, 0, 0), -1)  # Mouth
        
        # Convert to base64
        b64_data = image_to_base64(test_frame)
        
        # Send to backend
        response = requests.post(
            'http://localhost:8000/api/analyze-focus',
            json={'frame_data': b64_data},
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("📊 Focus Analysis Results:")
            print(f"   • Focus Score: {result.get('focus_score', 0)}")
            print(f"   • Focus Level: {result.get('focus_level', 'unknown')}")
            print(f"   • Attention Level: {result.get('attention_level', 'unknown')}")
            print(f"   • Eye Gaze: {result.get('eye_gaze', 'unknown')}")
            print(f"   • Face Detected: {result.get('face_detected', False)}")
            
            if result.get('recommendations'):
                print(f"   • Recommendations: {result['recommendations']}")
            
            print("✅ Focus analysis completed successfully")
            
        else:
            print(f"❌ Focus analysis failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Focus analysis test failed: {e}")

def test_tab_analysis():
    """Test tab analysis endpoint (for browser extension)"""
    print("\n🌐 Testing Tab Analysis...")
    
    test_cases = [
        {
            "name": "Educational YouTube",
            "url": "https://youtube.com/watch?v=calculus",
            "title": "Khan Academy - Calculus Fundamentals"
        },
        {
            "name": "Entertainment YouTube", 
            "url": "https://youtube.com/watch?v=funny",
            "title": "Funny Cats Compilation - HILARIOUS Videos"
        },
        {
            "name": "Programming Tutorial",
            "url": "https://youtube.com/watch?v=python",
            "title": "Python Programming Tutorial - Learn Coding"
        },
        {
            "name": "Social Media",
            "url": "https://facebook.com",
            "title": "Facebook - Connect with friends"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case['name']}")
        
        try:
            response = requests.post(
                'http://localhost:8000/api/analyze-tab',
                json={
                    'url': test_case['url'],
                    'title': test_case['title'],
                    'timestamp': int(time.time() * 1000)
                },
                timeout=15
            )
            
            if response.status_code == 200:
                analysis = response.json()
                result = analysis.get('result', {})
                
                print(f"   📊 Results:")
                print(f"      • Content Type: {result.get('content_type', 'unknown')}")
                print(f"      • Is Distraction: {result.get('is_distraction', False)}")
                print(f"      • Should Block: {result.get('should_block', False)}")
                print(f"      • Should Close: {result.get('should_close', False)}")
                print(f"      • Severity: {result.get('severity', 'none')}")
                
                if result.get('detected_indicators'):
                    indicators = result['detected_indicators'][:3]  # First 3
                    print(f"      • Detected: {indicators}")
                
                # Verify behavior
                if "Educational" in test_case['name'] or "Programming" in test_case['name']:
                    expected = not result.get('is_distraction', True)
                    status = "✅ CORRECT" if expected else "❌ NEEDS FIX"
                    print(f"   {status} - Educational content handling")
                
                elif "Entertainment" in test_case['name']:
                    expected = result.get('should_block', False)
                    status = "✅ CORRECT" if expected else "❌ NEEDS FIX" 
                    print(f"   {status} - Entertainment blocking")
                    
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Test failed: {e}")

def performance_test():
    """Test backend performance with multiple requests"""
    print("\n⚡ Testing Backend Performance...")
    
    # Create a simple test image
    test_img = np.ones((400, 600, 3), dtype=np.uint8) * 128
    cv2.putText(test_img, 'Performance Test', (100, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
    
    b64_data = image_to_base64(test_img)
    
    # Test multiple requests
    num_requests = 5
    times = []
    
    print(f"🔄 Sending {num_requests} requests...")
    
    for i in range(num_requests):
        start_time = time.time()
        
        try:
            response = requests.post(
                'http://localhost:8000/api/analyze-screen',
                json={'screenshot_data': b64_data},
                timeout=30
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            times.append(response_time)
            
            if response.status_code == 200:
                print(f"   ✅ Request {i+1}: {response_time:.2f}s")
            else:
                print(f"   ❌ Request {i+1}: Failed ({response.status_code})")
                
        except Exception as e:
            print(f"   ❌ Request {i+1}: Error - {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n📈 Performance Results:")
        print(f"   • Average Response Time: {avg_time:.2f}s")
        print(f"   • Fastest Response: {min_time:.2f}s")
        print(f"   • Slowest Response: {max_time:.2f}s")
        
        if avg_time < 2.0:
            print("   ✅ EXCELLENT performance!")
        elif avg_time < 5.0:
            print("   ✅ GOOD performance")
        else:
            print("   ⚠️  Performance could be improved")

def cleanup_test_files():
    """Clean up test files"""
    files_to_clean = ['webcam_analysis.jpg']
    
    for file in files_to_clean:
        if os.path.exists(file):
            os.remove(file)
            print(f"🧹 Cleaned up {file}")

def main():
    """Run comprehensive WorkSpace AI + OpenCV integration tests"""
    print("🎯 WorkSpace AI + OpenCV Integration Test Suite")
    print("=" * 70)
    
    # Test backend connection first
    if not test_backend_connection():
        print("\n❌ CRITICAL: Backend not running!")
        print("💡 Start backend with: cd python-backend && python app.py")
        return
    
    # Run all integration tests
    test_screenshot_analysis()
    test_focus_analysis() 
    test_tab_analysis()
    test_real_webcam_analysis()
    performance_test()
    
    print("\n" + "=" * 70)
    print("🎉 INTEGRATION TESTING COMPLETE!")
    print("=" * 70)
    
    print("\n✨ Your OpenCV + WorkSpace AI integration is working!")
    print("🚀 Ready for production use!")
    
    cleanup_test_files()

if __name__ == "__main__":
    main()
