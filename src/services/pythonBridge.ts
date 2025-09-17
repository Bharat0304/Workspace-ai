import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import axios, { AxiosResponse } from 'axios';
import { PythonAnalysisRequest, PythonAnalysisResponse, ActiveWindowInfo } from '../types';

class PythonBridge {
  private pythonServerUrl: string;
  private pythonPath: string;
  private pythonProcess: ChildProcess | null;

  constructor() {
    this.pythonServerUrl = process.env.PYTHON_SERVER_URL || 'http://localhost:8000';
    const currentDir = path.dirname(fileURLToPath(import.meta.url));
    this.pythonPath = path.join(currentDir, '../python_backend');
    this.pythonProcess = null;
  }

  async startPythonServer(): Promise<void> {
    return new Promise((resolve) => {
      try {
        const pythonScript = path.join(this.pythonPath, 'app.py');
        // Allow overriding python binary; prefer python3 then python
        const pythonBin = process.env.PYTHON_BIN || 'python3';

        this.pythonProcess = spawn(pythonBin, [pythonScript], {
          cwd: this.pythonPath,
        });

        this.pythonProcess.stdout?.on('data', (data: Buffer) => {
          console.log(`Python Backend: ${data.toString()}`);
        });

        this.pythonProcess.stderr?.on('data', (data: Buffer) => {
          console.error(`Python Backend Error: ${data.toString()}`);
        });

        // Handle spawn errors (e.g., ENOENT when python is missing)
        this.pythonProcess.on('error', (err: NodeJS.ErrnoException) => {
          console.warn(`Python backend not started (${err.code}). Continuing without Python.`);
          resolve();
        });

        this.pythonProcess.on('close', (code: number | null) => {
          console.log(`Python backend exited with code ${code}`);
        });

        // Resolve after 2s regardless to not block Node server
        setTimeout(() => resolve(), 2000);
      } catch (err) {
        console.warn('Failed to spawn Python process. Continuing without Python.');
        resolve();
      }
    });
  }

  async analyzeScreen(
    screenshotData: string,
    userId: string,
    sessionId: string
  ): Promise<PythonAnalysisResponse> {
    try {
      const requestData: PythonAnalysisRequest = {
        screenshot_data: screenshotData,
        user_id: userId,
        session_id: sessionId,
      };

      const response: AxiosResponse<PythonAnalysisResponse> = await axios.post(
        `${this.pythonServerUrl}/api/analyze-screen`,
        requestData,
        { timeout: 10000 }
      );
      
      return response.data;
    } catch (error) {
      console.error('Python screen analysis error:', (error as Error).message);
      throw error;
    }
  }

  async analyzeFocus(
    frameData: string,
    userId: string,
    sessionId: string
  ): Promise<PythonAnalysisResponse> {
    try {
      const requestData: PythonAnalysisRequest = {
        frame_data: frameData,
        user_id: userId,
        session_id: sessionId,
      };

      const response: AxiosResponse<PythonAnalysisResponse> = await axios.post(
        `${this.pythonServerUrl}/api/analyze-focus`,
        requestData,
        { timeout: 10000 }
      );
      
      return response.data;
    } catch (error) {
      console.error('Python focus analysis error:', (error as Error).message);
      throw error;
    }
  }

  async detectDistractions(
    windowInfo: ActiveWindowInfo,
    userId: string,
    sessionId: string
  ): Promise<PythonAnalysisResponse> {
    try {
      const requestData: PythonAnalysisRequest = {
        window_info: windowInfo,
        user_id: userId,
        session_id: sessionId,
      };

      const response: AxiosResponse<PythonAnalysisResponse> = await axios.post(
        `${this.pythonServerUrl}/api/detect-distractions`,
        requestData,
        { timeout: 5000 }
      );
      
      return response.data;
    } catch (error) {
      console.error('Python distraction detection error:', (error as Error).message);
      throw error;
    }
  }

  async analyzePosture(
    frameData: string,
    userId: string,
    sessionId: string
  ): Promise<PythonAnalysisResponse> {
    try {
      const requestData: PythonAnalysisRequest = {
        frame_data: frameData,
        user_id: userId,
        session_id: sessionId,
      };

      const response: AxiosResponse<PythonAnalysisResponse> = await axios.post(
        `${this.pythonServerUrl}/api/analyze-posture`,
        requestData,
        { timeout: 8000 }
      );
      
      return response.data;
    } catch (error) {
      console.error('Python posture analysis error:', (error as Error).message);
      throw error;
    }
  }

  stopPythonServer(): void {
    if (this.pythonProcess) {
      this.pythonProcess.kill();
      this.pythonProcess = null;
    }
  }
}

export default PythonBridge;
