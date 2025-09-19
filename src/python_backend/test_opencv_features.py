#!/usr/bin/env python3
"""
Test OpenCV features for WorkSpace AI backend
"""
import cv2
import numpy as np
import base64
import io
import os
from PIL import Image
import sys

def test_opencv_installation():
    """Test if OpenCV is properly installed"""
    print("🔍 Testing OpenCV Installation...")
    print(f"✅ OpenCV Version: {cv2.__version__}")
    print(f"✅ Python Version: {sys.version}")
    
    # Test basic OpenCV functionality
    try:
        # Create a simple test image
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        test_img[:] = [255, 0, 0]  # Blue image
        
        # Test basic operations
        gray = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        print("✅ Basic OpenCV operations working")
        return True
        
    except Exception as e:
        print(f"❌ OpenCV basic operations failed: {e}")
        return False

def test_webcam_access():
    """Test webcam access"""
    print("\n📷 Testing Webcam Access...")
    
    try:
        # Try to open webcam
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Cannot open webcam (camera index 0)")
            
            # Try different camera indices
            for i in range(1, 5):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    print(f"✅ Found camera at index {i}")
                    break
                cap.release()
            else:
                print("❌ No cameras found on indices 0-4")
                return False
        
        # Test reading a frame
        ret, frame = cap.read()
        if ret:
            print(f"✅ Successfully captured frame: {frame.shape}")
            print(f"   📐 Resolution: {frame.shape[1]}x{frame.shape[0]}")
            
            # Test saving the frame
            cv2.imwrite('test_frame.jpg', frame)
            print("✅ Frame saved as 'test_frame.jpg'")
            
        else:
            print("❌ Could not read frame from camera")
            cap.release()
            return False
            
        cap.release()
        return True
        
    except Exception as e:
        print(f"❌ Webcam test failed: {e}")
        return False

def test_image_processing():
    """Test various OpenCV image processing features"""
    print("\n🎨 Testing Image Processing Features...")
    
    try:
        # Create test image
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        
        # Draw some shapes for testing
        cv2.rectangle(img, (50, 50), (150, 150), (0, 255, 0), -1)  # Green rectangle
        cv2.circle(img, (300, 300), 50, (255, 0, 0), -1)  # Blue circle
        cv2.putText(img, 'TEST', (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 2)
        
        print("✅ Basic drawing operations working")
        
        # Test color space conversion
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        print("✅ Color space conversions working")
        
        # Test filtering
        blurred = cv2.GaussianBlur(img, (15, 15), 0)
        edges = cv2.Canny(gray, 50, 150)
        print("✅ Filtering operations working")
        
        # Test morphological operations
        kernel = np.ones((5, 5), np.uint8)
        morph = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        print("✅ Morphological operations working")
        
        # Test contour detection
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"✅ Found {len(contours)} contours")
        
        # Save test results
        cv2.imwrite('test_original.jpg', img)
        cv2.imwrite('test_gray.jpg', gray)
        cv2.imwrite('test_edges.jpg', edges)
        print("✅ Test images saved")
        
        return True
        
    except Exception as e:
        print(f"❌ Image processing test failed: {e}")
        return False

def test_base64_conversion():
    """Test base64 image conversion (crucial for web backends)"""
    print("\n🔄 Testing Base64 Conversion...")
    
    try:
        # Create test image
        img = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        
        # Convert to base64 (typical web format)
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        print(f"✅ Image to base64 conversion successful (length: {len(img_base64)})")
        
        # Convert back from base64
        img_bytes = base64.b64decode(img_base64)
        img_array = np.frombuffer(img_bytes, np.uint8)
        decoded_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if decoded_img is not None:
            print("✅ Base64 to image conversion successful")
            print(f"   📐 Original shape: {img.shape}")
            print(f"   📐 Decoded shape: {decoded_img.shape}")
            return True
        else:
            print("❌ Failed to decode base64 back to image")
            return False
            
    except Exception as e:
        print(f"❌ Base64 conversion test failed: {e}")
        return False

def test_face_detection():
    """Test face detection (common feature)"""
    print("\n👤 Testing Face Detection...")
    
    try:
        # Load face cascade (check if file exists)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        
        if not os.path.exists(cascade_path):
            print("❌ Face cascade file not found")
            return False
            
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if face_cascade.empty():
            print("❌ Could not load face cascade")
            return False
            
        print("✅ Face cascade loaded successfully")
        
        # Create test image with simple face-like pattern
        img = np.zeros((300, 300, 3), dtype=np.uint8)
        cv2.rectangle(img, (100, 100), (200, 200), (255, 255, 255), -1)  # Face area
        cv2.circle(img, (130, 130), 10, (0, 0, 0), -1)  # Eye
        cv2.circle(img, (170, 130), 10, (0, 0, 0), -1)  # Eye
        cv2.rectangle(img, (140, 160), (160, 180), (0, 0, 0), -1)  # Mouth
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        print(f"✅ Face detection completed, found {len(faces)} potential faces")
        
        # Draw rectangles around faces
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        cv2.imwrite('test_face_detection.jpg', img)
        print("✅ Face detection test image saved")
        
        return True
        
    except Exception as e:
        print(f"❌ Face detection test failed: {e}")
        return False

def test_video_processing():
    """Test video processing capabilities"""
    print("\n🎥 Testing Video Processing...")
    
    try:
        # Create a simple test video
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter('test_output.avi', fourcc, 20.0, (640, 480))
        
        if not out.isOpened():
            print("❌ Could not create video writer")
            return False
        
        print("✅ Video writer created successfully")
        
        # Generate some test frames
        for i in range(30):  # 30 frames
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # Add frame number
            cv2.putText(frame, f'Frame {i+1}', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            out.write(frame)
        
        out.release()
        print("✅ Test video created successfully")
        
        # Test reading the video back
        cap = cv2.VideoCapture('test_output.avi')
        
        if not cap.isOpened():
            print("❌ Could not open created video")
            return False
        
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"✅ Video properties - Frames: {frame_count}, FPS: {fps}, Size: {width}x{height}")
        
        cap.release()
        return True
        
    except Exception as e:
        print(f"❌ Video processing test failed: {e}")
        return False

def cleanup_test_files():
    """Clean up generated test files"""
    test_files = [
        'test_frame.jpg', 'test_original.jpg', 'test_gray.jpg', 'test_edges.jpg',
        'test_face_detection.jpg', 'test_output.avi'
    ]
    
    cleaned = 0
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            cleaned += 1
    
    if cleaned > 0:
        print(f"\n🧹 Cleaned up {cleaned} test files")

def main():
    """Run all OpenCV tests"""
    print("🚀 WorkSpace AI OpenCV Feature Test Suite")
    print("=" * 60)
    
    tests = [
        ("OpenCV Installation", test_opencv_installation),
        ("Webcam Access", test_webcam_access),
        ("Image Processing", test_image_processing),
        ("Base64 Conversion", test_base64_conversion),
        ("Face Detection", test_face_detection),
        ("Video Processing", test_video_processing),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY:")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 OVERALL: {passed}/{len(tests)} tests passed ({passed/len(tests)*100:.1f}%)")
    
    if passed == len(tests):
        print("🎉 ALL TESTS PASSED! Your OpenCV setup is working perfectly!")
    elif passed >= len(tests) * 0.8:
        print("⚠️  Most tests passed. Check failed tests above.")
    else:
        print("❌ Multiple tests failed. OpenCV setup needs attention.")
    
    # Cleanup
    cleanup_test_files()

if __name__ == "__main__":
    main()
