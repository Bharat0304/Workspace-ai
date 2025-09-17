// Shared app types

export type ID = string;

export interface User {
  id: ID;
  name?: string;
  email?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export type SessionStatus = 'active' | 'paused' | 'completed';

export interface Session {
  _id: ID;
  userId?: ID;
  subject?: string;
  status: SessionStatus;
  startTime: string; // ISO string
  endTime?: string;  // ISO string
  goalMinutes?: number;
}

export interface RealtimeUpdate {
  focusScore: number;
  distractionScore: number;
  productivityScore: number;
  eyeGaze: string;
  posture: string;
  activeWindow: string;
}
