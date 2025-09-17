import React, { useEffect, useRef, useState } from 'react';
import { socketService } from '../../services/socket';
import { useAuth } from '../../context/authContext';

interface Props {
  isActive: boolean;
  sessionId?: string;
  activeWindow: string;
  distractionScore: number;
}

export function ScreenMonitor({ isActive, sessionId, activeWindow, distractionScore }: Props) {
  const { user } = useAuth();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Start/stop screen capture based on isActive
  useEffect(() => {
    const startCapture = async () => {
      if (!isActive || !sessionId || !user) return;
      try {
        const media = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
        streamRef.current = media;
        if (videoRef.current) {
          videoRef.current.srcObject = media;
          await videoRef.current.play().catch(() => {});
        }
        // Periodically take snapshots to send via socket
        const sendFrame = async () => {
          if (!videoRef.current || !sessionId || !user) return;
          const vid = videoRef.current;
          const canvas = document.createElement('canvas');
          canvas.width = Math.min(vid.videoWidth || 1280, 640);
          canvas.height = Math.min(vid.videoHeight || 720, 360);
          const ctx = canvas.getContext('2d');
          if (!ctx) return;
          ctx.drawImage(vid, 0, 0, canvas.width, canvas.height);
          const dataUrl = canvas.toDataURL('image/jpeg', 0.6);
          socketService.sendScreenData(user.id, sessionId, { frame: dataUrl });
        };
        // 3s cadence
        intervalRef.current = window.setInterval(sendFrame, 3000);
        // send one immediately
        sendFrame();
        setError(null);
      } catch (e) {
        setError('Screen capture permission denied or unavailable.');
      }
    };

    const stopCapture = () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      streamRef.current?.getTracks().forEach(t => t.stop());
      streamRef.current = null;
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };

    if (isActive) {
      startCapture();
    } else {
      stopCapture();
    }

    return () => {
      stopCapture();
    };
  }, [isActive, sessionId, user]);

  return (
    <div className="bg-white rounded-2xl shadow-xl p-6">
      <h3 className="text-lg font-semibold mb-4">Screen Monitor</h3>
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <div className="text-sm text-gray-600">Active Window</div>
          <div className="text-gray-900 font-medium mb-4 break-all">{activeWindow || 'Unknown'}</div>
          <div className="text-sm text-gray-600">Distraction Score</div>
          <div className="text-gray-900 font-medium">{Math.round(distractionScore || 0)}</div>
          {!isActive && <div className="text-xs text-gray-400 mt-2">Monitoring paused</div>}
          {error && <div className="text-xs text-red-500 mt-2">{error}</div>}
        </div>
        <div>
          <video ref={videoRef} className="w-full rounded-lg bg-gray-100" muted playsInline />
        </div>
      </div>
    </div>
  );
}
