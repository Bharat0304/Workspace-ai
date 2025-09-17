import React, { useRef, useEffect, useState, useCallback } from 'react';
import Webcam from 'react-webcam';
import { Camera, CameraOff, Eye, User, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { socketService } from '../../services/socket';
import { useAuth } from '../../context/authContext';

interface CameraMonitorProps {
  isActive: boolean;
  sessionId?: string;
  onFocusUpdate: (data: {
    focusScore: number;
    eyeGaze: string;
    posture: string;
    faceDetected: boolean;
  }) => void;
  showPreview?: boolean; // when false, webcam stays hidden but analysis continues
}

export function CameraMonitor({ isActive, sessionId, onFocusUpdate, showPreview = false }: CameraMonitorProps) {
  const { user } = useAuth();
  const webcamRef = useRef<Webcam>(null);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [focusData, setFocusData] = useState({
    focusScore: 0,
    eyeGaze: 'forward',
    posture: 'good',
    faceDetected: false,
    emotionState: 'neutral'
  });
  const [cameraError, setCameraError] = useState<string | null>(null);

  // (moved below after function declarations to avoid TDZ issues)

  const startCamera = useCallback(async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ video: true });
      setIsCameraOn(true);
      setCameraError(null);
    } catch (error) {
      setCameraError('Camera access denied. Please enable camera permissions.');
      setIsCameraOn(false);
    }
  }, []);

  const stopCamera = useCallback(() => {
    setIsCameraOn(false);
  }, []);

  const captureFrame = useCallback(() => {
    if (!webcamRef.current || !sessionId) return;
    const imageSrc = webcamRef.current.getScreenshot();
    if (imageSrc) {
      const userId = user?.id || 'guest';
      socketService.sendCameraFrame(userId, sessionId, imageSrc);
    }
  }, [sessionId, user]);

  const startAnalysis = useCallback(() => {
    if (!isActive) return () => {};
    const interval = setInterval(() => {
      captureFrame();
    }, 3000); // Analyze every 3 seconds
    return () => clearInterval(interval);
  }, [isActive, captureFrame]);

  // Start/stop analysis timer when active/session changes
  useEffect(() => {
    if (!isActive || !sessionId) return;
    const cleanup = startAnalysis();
    return cleanup;
  }, [isActive, sessionId, startAnalysis]);

  // Auto-start/stop the camera with session lifecycle
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (isActive) {
        await startCamera();
        if (!cancelled) setCameraError(null);
      } else {
        stopCamera();
      }
    };
    run();
    return () => {
      cancelled = true;
      stopCamera();
    };
  }, [isActive, startCamera, stopCamera]);

  useEffect(() => {
    const handleFocusAnalysis = (data: any) => {
      const newFocusData = {
        focusScore: data.focusScore || 0,
        eyeGaze: data.eyeGaze || 'forward',
        posture: data.posture || 'good',
        faceDetected: data.faceDetected || false,
        emotionState: data.emotionState || 'neutral'
      };
      
      setFocusData(newFocusData);
      onFocusUpdate(newFocusData);
    };

    socketService.on('focus-analysis', handleFocusAnalysis);

    return () => {
      socketService.off('focus-analysis', handleFocusAnalysis);
    };
  }, [onFocusUpdate]);

  const getFocusColor = (score: number) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getPostureIcon = (posture: string) => {
    switch (posture) {
      case 'good':
        return '✅';
      case 'poor':
        return '⚠️';
      default:
        return '❓';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white rounded-2xl shadow-xl p-6"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Camera className="h-6 w-6 text-indigo-600" />
          <h2 className="text-xl font-semibold text-gray-900">Focus Monitor</h2>
        </div>
        <div className={`w-3 h-3 rounded-full ${isCameraOn ? 'bg-green-400' : 'bg-red-400'}`} />
      </div>

      <div className="space-y-6">
        {/* Camera Feed (hidden when showPreview=false) */}
        <div className="relative">
          {/* Keep webcam mounted invisibly so analysis can capture frames */}
          <div
            style={{ position: 'absolute', width: 1, height: 1, opacity: 0, pointerEvents: 'none' }}
            aria-hidden
          >
            {isCameraOn && !cameraError && (
              <Webcam
                ref={webcamRef}
                screenshotFormat="image/jpeg"
                videoConstraints={{ width: 640, height: 480, facingMode: 'user' }}
              />
            )}
          </div>

          {/* Placeholder card when preview is hidden */}
          {!showPreview && (
            <div className="aspect-video rounded-xl border border-gray-200 bg-gray-50 flex items-center justify-center">
              <div className="text-center px-6 py-8">
                <Camera className="h-8 w-8 mx-auto mb-2 text-indigo-600" />
                <p className="text-sm text-gray-600">Monitoring silently. Your camera preview is hidden during the session.</p>
              </div>
            </div>
          )}

          {/* Visible preview if explicitly enabled */}
          {showPreview && (
            <div className="aspect-video bg-gray-900 rounded-xl overflow-hidden">
              {isCameraOn && !cameraError ? (
                <Webcam
                  ref={webcamRef}
                  screenshotFormat="image/jpeg"
                  videoConstraints={{ width: 640, height: 480, facingMode: 'user' }}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  {cameraError ? (
                    <div className="text-center text-white">
                      <AlertCircle className="h-12 w-12 mx-auto mb-2 text-red-400" />
                      <p className="text-sm">{cameraError}</p>
                    </div>
                  ) : (
                    <div className="text-center text-white">
                      <CameraOff className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                      <p className="text-sm">Camera Off</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Analysis Overlay (only if preview is visible) */}
          {showPreview && (
            <AnimatePresence>
              {isActive && focusData.faceDetected && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute top-4 left-4 bg-black bg-opacity-70 text-white px-3 py-2 rounded-lg text-sm"
                >
                  <div className="flex items-center space-x-2">
                    <User className="h-4 w-4" />
                    <span>Face Detected</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          )}
        </div>

        {/* Focus Metrics */}
        {isActive && (
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Focus Score</span>
                <Eye className="h-4 w-4 text-indigo-600" />
              </div>
              <div className={`text-2xl font-bold ${getFocusColor(focusData.focusScore)}`}>
                {focusData.focusScore}%
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <motion.div
                  className="bg-gradient-to-r from-indigo-500 to-blue-500 h-2 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${focusData.focusScore}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>

            <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Posture</span>
                <span className="text-lg">{getPostureIcon(focusData.posture)}</span>
              </div>
              <div className="text-lg font-semibold text-gray-900 capitalize">
                {focusData.posture}
              </div>
              <div className="text-sm text-gray-500 mt-1">
                Eye Gaze: {focusData.eyeGaze}
              </div>
            </div>
          </div>
        )}

        {/* Real-time Recommendations */}
        {isActive && focusData.focusScore < 70 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-yellow-50 border border-yellow-200 rounded-xl p-4"
          >
            <div className="flex items-center space-x-2 mb-2">
              <AlertCircle className="h-5 w-5 text-yellow-600" />
              <span className="font-medium text-yellow-800">Focus Improvement</span>
            </div>
            <ul className="text-sm text-yellow-700 space-y-1">
              <li>• Sit up straight and align your shoulders</li>
              <li>• Look directly at your study material</li>
              <li>• Take a few deep breaths to refocus</li>
            </ul>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
