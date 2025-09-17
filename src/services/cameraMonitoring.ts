import { Server as SocketIOServer, Socket } from 'socket.io';
import mongoose from 'mongoose';
import Session from '../models/Session';
import PythonBridge from './pythonBridge';
import { CameraData, PythonAnalysisResponse } from '../types';

class CameraMonitoringService {
  private io: SocketIOServer;
  private pythonBridge: PythonBridge;

  constructor(io: SocketIOServer, pythonBridge: PythonBridge) {
    this.io = io;
    this.pythonBridge = pythonBridge;
  }

  async processCameraFrame(socket: Socket, data: any): Promise<void> {
    try {
      const { userId, sessionId, frameData }: { userId: string; sessionId: string; frameData: string } = data;
      console.log('[camera] frame received', { userId, sessionId, size: frameData?.length || 0 });
      
      // Send frame to Python for AI analysis
      const [focusAnalysis, postureAnalysis]: PythonAnalysisResponse[] = await Promise.all([
        this.pythonBridge.analyzeFocus(frameData, userId, sessionId),
        this.pythonBridge.analyzePosture(frameData, userId, sessionId),
      ]);

      // Python responses are shaped as { success, analysis_type, user_id, session_id, result: {...} }
      // Unwrap `.result` so our emit has direct fields
      const focusPayload = (focusAnalysis as any)?.result ?? focusAnalysis;
      const posturePayload = (postureAnalysis as any)?.result ?? postureAnalysis;

      // Combine analysis results
      const combinedAnalysis: PythonAnalysisResponse & { timestamp: Date } = {
        ...(focusPayload as any),
        ...(posturePayload as any),
        timestamp: new Date(),
      };

      // Store camera data
      const cameraData: CameraData = {
        userId,
        sessionId,
        timestamp: new Date(),
        focusScore: combinedAnalysis.focus_score || 50,
        eyeGaze: combinedAnalysis.eye_gaze || 'forward',
        posture: combinedAnalysis.posture_status || 'good',
        faceDetected: combinedAnalysis.face_detected || false,
        emotionState: combinedAnalysis.emotion || 'neutral',
        attentionLevel: combinedAnalysis.attention_level || 'medium',
        aiAnalysis: combinedAnalysis,
      };

      // Update session
      if (mongoose.isValidObjectId(sessionId)) {
        console.log('[camera] storing cameraData into Session...');
        await Session.findByIdAndUpdate(sessionId, {
          $push: { cameraData },
        });
      } else {
        console.warn('[camera] Skipping DB write: sessionId is not a valid ObjectId ->', sessionId);
      }

      // Emit real-time feedback
      socket.emit('focus-analysis', {
        focusScore: combinedAnalysis.focus_score,
        eyeGaze: combinedAnalysis.eye_gaze,
        posture: combinedAnalysis.posture_status,
        emotionState: combinedAnalysis.emotion,
        attentionLevel: combinedAnalysis.attention_level,
        faceDetected: combinedAnalysis.face_detected,
        recommendations: combinedAnalysis.recommendations || [],
        alerts: [], // You can add alerts logic here
      });

      // Trigger alerts if focus is low
      if ((combinedAnalysis.focus_score || 50) < 50) {
        console.warn('[camera] low focus detected, emitting low-focus-alert');
        socket.emit('low-focus-alert', {
          focusScore: combinedAnalysis.focus_score,
          suggestions: [], // Add improvement suggestions here
        });
      }

    } catch (error) {
      console.error('Camera processing error:', error);
      socket.emit('camera-error', { error: (error as Error).message });
    }
  }
}

export default CameraMonitoringService;
