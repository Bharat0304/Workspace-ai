import screenshot from 'screenshot-desktop';
import activeWindow from 'active-win';
import mongoose from 'mongoose';
import { Server as SocketIOServer, Socket } from 'socket.io';
import { createRequire } from 'module';
import Session from '../models/Session';
import PythonBridge from './pythonBridge';
import { ActiveWindowInfo, MonitoringData, PythonAnalysisResponse } from '../types';


class ScreenMonitoringService {
  private io: SocketIOServer;
  private pythonBridge: PythonBridge;
  private monitoringIntervals: Map<string, NodeJS.Timeout>;

  constructor(io: SocketIOServer, pythonBridge: PythonBridge) {
    this.io = io;
    this.pythonBridge = pythonBridge;
    this.monitoringIntervals = new Map();
  }

  async startMonitoring(userId: string, sessionId: string): Promise<void> {
    if (this.monitoringIntervals.has(userId)) {
      this.stopMonitoring(userId);
    }

    console.log(`[monitoring] startMonitoring user=${userId} session=${sessionId}`);

    const interval = setInterval(async () => {
      try {
        await this.captureAndAnalyzeScreen(userId, sessionId);
      } catch (error) {
        console.error('Screen monitoring error:', error);
      }
    }, 5000);

    this.monitoringIntervals.set(userId, interval);

    // Fire an immediate capture so the user doesn't need to wait 5 seconds
    try {
      console.log('[monitoring] immediate capture triggered');
      await this.captureAndAnalyzeScreen(userId, sessionId);
    } catch (error) {
      console.error('[monitoring] immediate capture failed:', error);
    }
  }

  stopMonitoring(userId: string): void {
    const interval = this.monitoringIntervals.get(userId);
    if (interval) {
      clearInterval(interval);
      this.monitoringIntervals.delete(userId);
    }
  }

  async captureAndAnalyzeScreen(userId: string, sessionId: string): Promise<void> {
    try {
      console.log('[monitoring] capturing screenshot...');
      // Capture screenshot
      const screenshotBuffer: Buffer = await screenshot();
      console.log(`[monitoring] screenshot captured bytes=${screenshotBuffer?.length ?? 0}`);
      const screenshotBase64: string = screenshotBuffer.toString('base64');
      
      // Get active window information (v8.x API)
      console.log('[monitoring] reading active window info...');
      const activeWindowInfo = await activeWindow();
      console.log(`[monitoring] active window title="${activeWindowInfo?.title ?? 'Unknown'}" owner="${activeWindowInfo?.owner?.name ?? 'Unknown'}"`);
      
      // Upload to Cloudinary (lazy load, optional)
      let uploadUrl: string | undefined = undefined;
      try {
        const require = createRequire(import.meta.url);
        const cloudinaryMod = require('cloudinary');
        const cloudinary = (cloudinaryMod.v2 ?? cloudinaryMod);
        if (cloudinary && cloudinary.uploader) {
          console.log('[monitoring] uploading screenshot to Cloudinary...');
          const cfg: { cloud_name?: string; api_key?: string; api_secret?: string } = {};
          if (process.env.CLOUDINARY_CLOUD_NAME) cfg.cloud_name = process.env.CLOUDINARY_CLOUD_NAME;
          if (process.env.CLOUDINARY_API_KEY) cfg.api_key = process.env.CLOUDINARY_API_KEY;
          if (process.env.CLOUDINARY_API_SECRET) cfg.api_secret = process.env.CLOUDINARY_API_SECRET;
          if (cloudinary.config) cloudinary.config(cfg);

          const result = await new Promise<any>((resolve, reject) => {
            cloudinary.uploader.upload_stream(
              {
                resource_type: 'image',
                folder: `workspace-ai/screenshots/${userId}`,
                public_id: `screenshot_${Date.now()}`,
              },
              (error: any, res: any) => {
                if (error) reject(error);
                else resolve(res);
              }
            ).end(screenshotBuffer);
          });
          uploadUrl = result?.secure_url;
          console.log(`[monitoring] cloudinary upload success url=${uploadUrl}`);
        }
      } catch (e) {
        // Cloudinary not available; proceed without upload
        console.warn('[monitoring] Cloudinary not available or failed to load. Skipping upload.');
      }

      // Send to Python for AI analysis
      console.log('[monitoring] calling Python /api/analyze-screen ...');
      const analysisPromises: Promise<PythonAnalysisResponse>[] = [
        this.pythonBridge.analyzeScreen(screenshotBase64, userId, sessionId),
      ];

      if (activeWindowInfo) {
        console.log('[monitoring] calling Python /api/detect-distractions ...');
        analysisPromises.push(
          this.pythonBridge.detectDistractions(activeWindowInfo as ActiveWindowInfo, userId, sessionId)
        );
      }

      const [screenAnalysis, distractionAnalysis] = await Promise.all(analysisPromises);
      console.log('[monitoring] python responses received', {
        screenKeys: Object.keys(screenAnalysis || {}),
        distractionKeys: Object.keys(distractionAnalysis || {}),
      });

      // Combine analysis results
      const analysisResult: PythonAnalysisResponse & { activeWindow?: any; screenshotUrl?: string } = {
        ...screenAnalysis,
        ...distractionAnalysis,
        activeWindow: activeWindowInfo,
        ...(uploadUrl ? { screenshotUrl: uploadUrl } : {}),
      };

      // Store monitoring data
      const monitoringData: MonitoringData = {
        userId,
        sessionId,
        timestamp: new Date(),
        activeWindow: activeWindowInfo as ActiveWindowInfo,
        ...(uploadUrl ? { screenshotUrl: uploadUrl } : {}),
        isDistraction: analysisResult.is_distraction || false,
        focusLevel: analysisResult.focus_level || 'medium',
        distractionScore: analysisResult.distraction_score || 0,
        productivityScore: analysisResult.productivity_score || 50,
        aiAnalysis: analysisResult,
      };

      // Update session
      if (mongoose.isValidObjectId(sessionId)) {
        console.log('[monitoring] storing monitoringData into Session...');
        await Session.findByIdAndUpdate(sessionId, {
          $push: { monitoringData },
        });
      } else {
        console.warn('[monitoring] Skipping DB write: sessionId is not a valid ObjectId ->', sessionId);
      }

      // Emit real-time data
      console.log(`[monitoring] emitting screen-analysis to room user-${userId}`);
      this.io.to(`user-${userId}`).emit('screen-analysis', {
        activeWindow: activeWindowInfo?.title || 'Unknown',
        isDistraction: analysisResult.is_distraction,
        focusLevel: analysisResult.focus_level,
        distractionScore: analysisResult.distraction_score,
        productivityScore: analysisResult.productivity_score,
        recommendations: analysisResult.recommendations || [],
        timestamp: new Date(),
      });

      // Trigger intervention if needed
      if (analysisResult.is_distraction && (analysisResult.distraction_score || 0) > 0.7) {
        console.log('[monitoring] high distraction detected, emitting distraction-detected');
        this.io.to(`user-${userId}`).emit('distraction-detected', {
          app: activeWindowInfo?.owner?.name || 'Unknown App',
          action: analysisResult.suggested_action || 'close-tab',
          severity: analysisResult.distraction_score,
        });
      }

    } catch (error) {
      console.error('[monitoring] Screen analysis error:', error);
      // Common macOS permission hints
      console.error('[monitoring] If this persists on macOS, ensure Terminal/IDE has Screen Recording and Accessibility permissions, then restart it.');
    }
  }

  processScreenData(socket: Socket, data: any): void {
    const { userId, sessionId, activeTab, browserInfo } = data;
    
    socket.emit('screen-processed', {
      status: 'processed',
      timestamp: new Date(),
    });
  }
}

export default ScreenMonitoringService;
