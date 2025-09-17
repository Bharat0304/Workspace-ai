import axios from 'axios';
import { toast } from 'react-hot-toast';
import type { User, Session } from '../types';

type AxiosInstance = ReturnType<typeof axios.create>;

class ApiService {
  private api: AxiosInstance;

  constructor() {
    // Normalize base URL: allow VITE_API_URL to be either 'http://host:port' or 'http://host:port/api'
    const rawBase: string = (import.meta as any).env.VITE_API_URL || 'http://localhost:5001/api';
    const baseURL = /\/api\/?$/.test(rawBase) ? rawBase.replace(/\/$/, '') : `${rawBase.replace(/\/$/, '')}/api`;

    this.api = axios.create({
      baseURL,
      timeout: 10000,
    });

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token');
        if (token) {
          config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        // If unauthorized, clear token but do not force redirect; allow guest-mode fallbacks
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
        }
        
        const message = error.response?.data?.message || 'An error occurred';
        toast.error(message);
        
        return Promise.reject(error);
      }
    );
  }

  // Auth endpoints
  async login(email: string, password: string): Promise<{ user: User; token: string }> {
    const response = await this.api.post('/auth/login', { email, password });
    return response.data.data;
  }

  async register(name: string, email: string, password: string): Promise<{ user: User; token: string }> {
    const response = await this.api.post('/auth/register', { name, email, password });
    return response.data.data;
  }

  async getProfile(): Promise<User> {
    const response = await this.api.get('/auth/me');
    return response.data.data.user;
  }

  async updateProfile(data: Partial<User>): Promise<User> {
    const response = await this.api.put('/auth/update-profile', data);
    return response.data.data.user;
  }

  // Session endpoints
  async startSession(data: { subject?: string; goalMinutes: number }): Promise<Session> {
    try {
      const response = await this.api.post('/session/start', data);
      return response.data.data.session;
    } catch (_err: any) {
      // Fallback: create a synthetic session so we can still start monitoring (guest/dev mode)
      const now = new Date().toISOString();
      const session: Session = {
        _id: (typeof crypto !== 'undefined' && (crypto as any).randomUUID) ? (crypto as any).randomUUID() : `${Date.now()}`,
        subject: data.subject,
        goalMinutes: data.goalMinutes,
        status: 'active',
        startTime: now,
      } as Session;
      toast.success('Started session in guest mode');
      return session;
    }
  }

  async pauseSession(sessionId: string): Promise<Session> {
    try {
      const response = await this.api.put(`/session/${sessionId}/pause`);
      return response.data.data.session;
    } catch (_err: any) {
      // Fallback: no-op; return a paused session shape
      toast('Paused session (guest mode)');
      return {
        _id: sessionId,
        status: 'paused',
        startTime: new Date().toISOString(),
      } as Session;
    }
  }

  async resumeSession(sessionId: string): Promise<Session> {
    try {
      const response = await this.api.put(`/session/${sessionId}/resume`);
      return response.data.data.session;
    } catch (_err: any) {
      toast.success('Resumed session (guest mode)');
      return {
        _id: sessionId,
        status: 'active',
        startTime: new Date().toISOString(),
      } as Session;
    }
  }

  async endSession(sessionId: string): Promise<Session> {
    try {
      const response = await this.api.put(`/session/${sessionId}/end`);
      return response.data.data.session;
    } catch (_err: any) {
      toast.success('Ended session (guest mode)');
      return {
        _id: sessionId,
        status: 'completed',
        startTime: new Date().toISOString(),
        endTime: new Date().toISOString(),
      } as Session;
    }
  }

  async getCurrentSession(): Promise<Session | null> {
    try {
      const response = await this.api.get('/session/current');
      return response.data.data.session;
    } catch (error) {
      return null;
    }
  }

  async getSessionHistory(page = 1, limit = 10): Promise<{
    sessions: Session[];
    pagination: any;
  }> {
    const response = await this.api.get(`/session/history?page=${page}&limit=${limit}`);
    return response.data.data;
  }

  async getSessionStats(): Promise<any> {
    const response = await this.api.get('/session/stats/overview');
    return response.data.data.overview;
  }

  // Monitoring endpoints
  async startMonitoring(sessionId: string, userId: string): Promise<void> {
    await this.api.post('/monitoring/start', { sessionId, userId });
  }

  async stopMonitoring(userId: string): Promise<void> {
    await this.api.post('/monitoring/stop', { userId });
  }

  // Intervention endpoints
  async triggerIntervention(sessionId: string, type: string, data: any): Promise<void> {
    await this.api.post('/intervention/trigger', { sessionId, type, data });
  }

  async getInterventionStats(timeframe = 'week'): Promise<any> {
    const response = await this.api.get(`/intervention/stats?timeframe=${timeframe}`);
    return response.data.data.stats;
  }
}

export const apiService = new ApiService();
