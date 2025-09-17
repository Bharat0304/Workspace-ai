export interface User {
    id: string;
    name: string;
    email: string;
    createdAt: Date;
    updatedAt: Date;
  }
  
  export interface Session {
    _id: string;
    userId: string;
    startTime: Date;
    endTime?: Date;
    duration?: number;
    subject?: string;
    goalMinutes?: number;
    status: 'active' | 'paused' | 'completed' | 'interrupted';
    monitoringData: MonitoringData[];
    cameraData: CameraData[];
    interventions: Intervention[];
    productivity: ProductivityMetrics;
  }
  
  export interface MonitoringData {
    userId: string;
    sessionId: string;
    timestamp: Date;
    activeWindow?: ActiveWindowInfo;
    screenshotUrl?: string;
    isDistraction: boolean;
    focusLevel: string;
    distractionScore?: number;
    productivityScore?: number;
    aiAnalysis?: any;
  }
  
  export interface CameraData {
    userId: string;
    sessionId: string;
    timestamp: Date;
    focusScore: number;
    eyeGaze: string;
    posture: string;
    faceDetected: boolean;
    emotionState?: string;
    attentionLevel?: string;
    aiAnalysis?: any;
  }
  
  export interface ActiveWindowInfo {
    title: string;
    owner: {
      name: string;
      processId: number;
    };
    url?: string;
    bounds: {
      x: number;
      y: number;
      width: number;
      height: number;
    };
  }
  
  export interface Intervention {
    userId: string;
    sessionId: string;
    type: string;
    timestamp: Date;
    data: any;
    executed: boolean;
  }
  
  export interface ProductivityMetrics {
    focusPercentage: number;
    distractionCount: number;
    averageFocusScore: number;
    totalBreaks: number;
  }
  
  export interface PythonAnalysisRequest {
    screenshot_data?: string;
    frame_data?: string;
    window_info?: ActiveWindowInfo;
    user_id: string;
    session_id: string;
  }
  
  export interface PythonAnalysisResponse {
    focus_score?: number;
    focus_level?: string;
    productivity_score?: number;
    distraction_score?: number;
    is_distraction?: boolean;
    content_type?: string;
    suggested_action?: string;
    recommendations?: string[];
    eye_gaze?: string;
    face_detected?: boolean;
    attention_level?: string;
    emotion?: string;
    posture_status?: string;
    analysis_timestamp?: string;
  }
  
  export interface SocketEvents {
    'join-session': (userId: string) => void;
    'screen-data': (data: any) => void;
    'camera-frame': (data: any) => void;
    'screen-analysis': (data: any) => void;
    'focus-analysis': (data: any) => void;
    'distraction-detected': (data: any) => void;
    'python-analysis-result': (data: any) => void;
  }
  