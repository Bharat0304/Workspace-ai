import { io, Socket } from 'socket.io-client';

class SocketService {
  private socket: Socket | null = null;
  private listeners: Map<string, Function[]> = new Map();

  connect(userId: string): void {
    if (this.socket?.connected) return;

    const raw = (import.meta as any).env.VITE_API_URL || 'http://localhost:5001';
    const url = /\/api\/?$/.test(raw) ? raw.replace(/\/api\/?$/, '') : raw;

    this.socket = io(url, {
      auth: {
        token: localStorage.getItem('token')
      }
    });

    this.socket.on('connect', () => {
      console.log('Connected to server');
      this.socket?.emit('join-session', userId);
    });

    this.socket.on('disconnect', () => {
      console.log('Disconnected from server');
    });

    // Real-time event handlers
    this.socket.on('screen-analysis', (data) => {
      this.emit('screen-analysis', data);
    });

    this.socket.on('focus-analysis', (data) => {
      this.emit('focus-analysis', data);
    });

    this.socket.on('distraction-detected', (data) => {
      this.emit('distraction-detected', data);
    });

    this.socket.on('python-analysis-result', (data) => {
      this.emit('python-analysis-result', data);
    });

    this.socket.on('close-tab', (data) => {
      this.emit('close-tab', data);
    });

    this.socket.on('show-reminder', (data) => {
      this.emit('show-reminder', data);
    });

    this.socket.on('break-suggestion', (data) => {
      this.emit('break-suggestion', data);
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  // Send camera frame for analysis
  sendCameraFrame(userId: string, sessionId: string, frameData: string): void {
    this.socket?.emit('camera-frame', {
      userId,
      sessionId,
      frameData
    });
  }

  // Send screen data
  sendScreenData(userId: string, sessionId: string, data: any): void {
    this.socket?.emit('screen-data', {
      userId,
      sessionId,
      ...data
    });
  }

  // Enforcement helpers
  requestCloseTab(domain: string): void {
    this.socket?.emit('close-tab', { domain });
  }

  updateAllowlist(allow: string[], block: string[]): void {
    this.socket?.emit('allowlist-update', { allow, block });
  }

  // Event listener management
  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)?.push(callback);
  }

  off(event: string, callback: Function): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      const index = eventListeners.indexOf(callback);
      if (index > -1) {
        eventListeners.splice(index, 1);
      }
    }
  }

  private emit(event: string, data: any): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(callback => callback(data));
    }
  }
}

export const socketService = new SocketService();
