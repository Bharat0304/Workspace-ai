// ============================================
// CORE DATA TYPES
// ============================================

export interface TabData {
    timestamp: number;
    tabCount: number;
    activeTab: string;
    duplicates: string[];
    idleTabs: string[];
    screenshotUrl?: string;
    productivityScore?: number;
  }
  
  export interface DuplicateTab {
    title: string;
    url: string;
    similarity: number;
    tabIds: string[];
  }
  
  export interface IdleTab {
    title: string;
    url: string;
    lastActiveTime: number;
    idleDuration: number; // in seconds
  }
  
  // ============================================
  // PYTHON BRIDGE TYPES
  // ============================================
  
  export interface PythonBridgeResult {
    timestamp: number;
    tab_count: number;
    active_tab: string;
    duplicates: string[];
    idle_tabs: string[];
    screenshot?: string; // Base64 encoded image
    productivity_score?: number;
  }
  
  export interface PythonAnalysisOptions {
    includeScreenshot: boolean;
    detectDuplicates: boolean;
    trackIdleTabs: boolean;
    screenshotQuality: 'low' | 'medium' | 'high';
  }
  
  // ============================================
  // API REQUEST/RESPONSE TYPES
  // ============================================
  
  export interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
    timestamp?: number;
  }
  
  export interface AnalyzeRequest {
    options?: PythonAnalysisOptions;
  }
  
  export interface AnalyzeResponse extends ApiResponse<TabData> {}
  
  export interface HealthCheckResponse extends ApiResponse<{
    server: string;
    python: boolean;
    cloudinary: boolean;
    uptime: number;
  }> {}
  
  // ============================================
  // SOCKET.IO EVENT TYPES
  // ============================================
  
  export interface SocketEvents {
    'join-session': (userId: string) => void;
    'screen-data': (data: any) => void;
    'camera-frame': (data: any) => void;
    'screen-analysis': (data: any) => void;
    'focus-analysis': (data: any) => void;
    'distraction-detected': (data: any) => void;
    'python-analysis-result': (data: any) => void;
  }

  export interface ServerToClientEvents {
    'tab-update': (data: TabData) => void;
    'error': (error: string) => void;
    'monitoring-started': () => void;
    'monitoring-stopped': () => void;
    'duplicate-detected': (duplicates: DuplicateTab[]) => void;
    'idle-tabs-found': (idleTabs: IdleTab[]) => void;
  }
  
  export interface ClientToServerEvents {
    'start-monitoring': (options?: MonitoringOptions) => void;
    'stop-monitoring': () => void;
    'analyze-now': (options?: PythonAnalysisOptions) => void;
  }
  
  export interface MonitoringOptions {
    interval: number; // in milliseconds
    includeScreenshots: boolean;
    detectDuplicates: boolean;
    trackProductivity: boolean;
  }
  
  // ============================================
  // CLOUDINARY TYPES
  // ============================================
  
  export interface CloudinaryUploadResult {
    publicId: string;
    secureUrl: string;
    width: number;
    height: number;
    bytes: number;
    format: string;
    createdAt: string;
  }
  
  export interface ScreenshotMetadata {
    userId?: string;
    timestamp: number;
    analysis: TabData;
    cloudinaryData: CloudinaryUploadResult;
  }
  
  // ============================================
  // ERROR HANDLING TYPES
  // ============================================
  
  export interface ErrorInfo {
    code: string;
    message: string;
    timestamp: number;
    context?: string;
    stack?: string;
  }
  
  export type ErrorCode = 
    | 'PYTHON_BRIDGE_ERROR'
    | 'CLOUDINARY_UPLOAD_ERROR' 
    | 'SCREENSHOT_CAPTURE_ERROR'
    | 'ANALYSIS_FAILED'
    | 'INVALID_REQUEST'
    | 'SERVER_ERROR';
  
  // ============================================
  // MONITORING SESSION TYPES
  // ============================================
  
  export interface MonitoringSession {
    sessionId: string;
    startTime: number;
    endTime?: number;
    isActive: boolean;
    options: MonitoringOptions;
    dataPoints: TabData[];
    totalScreenshots: number;
    duplicatesDetected: number;
    idleTabsClosed: number;
  }
  
  // ============================================
  // UTILITY TYPES
  // ============================================
  
  export type LogLevel = 'error' | 'warn' | 'info' | 'debug';
  
  export interface LogEntry {
    level: LogLevel;
    message: string;
    timestamp: number;
    context?: string;
    metadata?: Record<string, any>;
  }
  
  // ============================================
  // CONFIGURATION TYPES
  // ============================================
  
  export interface ServerConfig {
    port: number;
    cors: {
      origin: string;
      credentials: boolean;
    };
    socketIO: {
      pingTimeout: number;
      pingInterval: number;
    };
  }
  
  export interface PythonConfig {
    pythonPath: string;
    scriptPath: string;
    timeout: number;
    maxRetries: number;
  }
  
  export interface CloudinaryConfig {
    cloudName: string;
    apiKey: string;
    apiSecret: string;
    folder: string;
    uploadPreset?: string;
  }
  
  // ============================================
  // EXPRESS REQUEST EXTENSIONS
  // ============================================
  
  declare global {
    namespace Express {
      interface Request {
        sessionId?: string;
        startTime?: number;
      }
    }
  }
  
  // ============================================
  // ENVIRONMENT VARIABLES TYPE
  // ============================================
  
  export interface EnvironmentVariables {
    NODE_ENV: 'development' | 'production' | 'test';
    PORT: string;
    CLIENT_URL: string;
    PYTHON_PATH: string;
    CLOUDINARY_CLOUD_NAME: string;
    CLOUDINARY_API_KEY: string;
    CLOUDINARY_API_SECRET: string;
  }

  // Re-export all types from types/index.ts
  export * from './types/index';
  