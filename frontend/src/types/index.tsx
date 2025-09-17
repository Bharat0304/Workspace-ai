export interface User {
    id: string;
    name: string;
    email: string;
    avatar?: string;
    role: 'student' | 'admin';
    preferences: UserPreferences;
    stats: UserStats;
    lastLogin?: Date;
    createdAt: Date;
  }
  
  export interface UserPreferences {
    studyGoals: string[];
    distractingApps: string[];
    workingHours: {
      start: string;
      end: string;
    };
    breakReminders: boolean;
    focusMode: 'strict' | 'moderate' | 'flexible';
  }
  
  export interface UserStats {
    totalStudyTime: number;
    totalSessions: number;
    averageFocusScore: number;
    longestSession: number;
    streakDays: number;
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
    timestamp: Date;
    activeWindow?: string;
    screenshotUrl?: string;
    isDistraction: boolean;
    focusLevel: string;
    distractionScore?: number;
    productivityScore?: number;
  }
  
  export interface CameraData {
    timestamp: Date;
    focusScore: number;
    eyeGaze: string;
    posture: string;
    faceDetected: boolean;
    emotionState?: string;
    attentionLevel?: string;
  }
  
  export interface Intervention {
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
  
  export interface RealtimeUpdate {
    type: 'screen-analysis' | 'focus-analysis' | 'distraction-detected' | 'intervention';
    data: any;
    timestamp: Date;
  }
  
  export interface AuthState {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    isAuthenticated: boolean;
  }
  