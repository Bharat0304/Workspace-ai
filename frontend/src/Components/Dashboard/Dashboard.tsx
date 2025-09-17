import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, Square, Camera, Monitor, Target, TrendingUp } from 'lucide-react';
import { useAuth } from '../../context/authContext';
import { apiService } from '../../services/api';
import { socketService } from '../../services/socket';
import type { Session } from '../../types';
import { CameraMonitor } from './CameraMonitor';
import { ScreenMonitor } from './ScreenMonitor';
import { SessionControls } from './SessionControls';
import { RealTimeStats } from './RealTimeStats';
import { InterventionPanel } from './InterventionPanel';
import { toast } from 'react-hot-toast';

// Simple SVG sparkline component (module scope)
function Sparkline({ values, height = 40 }: { values: number[]; height?: number }) {
  const width = 600; // intrinsic width; SVG scales via CSS
  const h = height;
  const padding = 4;
  const n = values.length;
  const data = n > 0 ? values : [0, 0];
  const maxV = 100; // focus is 0-100
  const minV = 0;
  const xFor = (i: number) => (n <= 1 ? padding : padding + (i * (width - padding * 2)) / (n - 1));
  const yFor = (v: number) => padding + (h - padding * 2) * (1 - (v - minV) / (maxV - minV));
  const path = data
    .map((v, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i).toFixed(2)} ${yFor(v).toFixed(2)}`)
    .join(' ');

  // Color by ending value
  const end = values.length ? values[values.length - 1] : 0;
  const strokeColor = end >= 80 ? '#10b981' : end >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div className="w-full overflow-hidden rounded-lg border border-gray-200 bg-gray-50">
      <svg viewBox={`0 0 ${width} ${h}`} preserveAspectRatio="none" className="w-full h-16">
        <path d={path} fill="none" stroke={strokeColor} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        <line x1="0" y1={yFor(50)} x2={width} y2={yFor(50)} stroke="#e5e7eb" strokeDasharray="4 4" />
      </svg>
    </div>
  );
}

export function Dashboard() {
  const { user } = useAuth();
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [lockUrl, setLockUrl] = useState<string>('');
  // Timer state
  const [accumulatedMs, setAccumulatedMs] = useState<number>(0);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const [timerTick, setTimerTick] = useState<number>(0); // used to trigger re-render every second
  const [focusSamples, setFocusSamples] = useState<Array<{ score: number; posture: string; ts: number }>>([]);
  const [sessionSummary, setSessionSummary] = useState<null | {
    avgFocus: number;
    minFocus: number;
    maxFocus: number;
    totalSamples: number;
    postureCounts: Record<string, number>;
    durationMs?: number;
    focusSeries?: number[];
  }>(null);
  // Allowed educational domains; block list can include distracting sites
  const ALLOWLIST = [
    'wikipedia.org',
    'khanacademy.org',
    'coursera.org',
    'edx.org',
    'docs.google.com',
    'stackoverflow.com',
    'stackexchange.com',
    'unacademy.com',
    'physicswallah.live',
    'pw.live',
    'youtube.com', // will be filtered by content check
  ];
  const BLOCKLIST = ['instagram.com', 'instagr.am'];
  const [realtimeData, setRealtimeData] = useState<{
    focusScore: number;
    distractionScore: number;
    productivityScore: number;
    eyeGaze: string;
    posture: string;
    activeWindow: string;
  }>({
    focusScore: 0,
    distractionScore: 0,
    productivityScore: 0,
    eyeGaze: 'forward',
    posture: 'good',
    activeWindow: 'Unknown'
  });

  useEffect(() => {
    // Ensure socket is connected even if user is not authenticated
    try {
      socketService.connect(user?.id || 'guest');
    } catch (e) {
      // ignore
    }
  }, [user?.id]);

  useEffect(() => {
    loadCurrentSession();
    setupSocketListeners();

    return () => {
      // Cleanup socket listeners
    };
  }, []);

  // ---- Timer helpers ----
  const startTimer = () => {
    if (startedAt != null) return; // already running
    const now = Date.now();
    setStartedAt(now);
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = window.setInterval(() => {
      setTimerTick(Date.now());
    }, 1000);
  };

  const pauseTimer = () => {
    if (startedAt != null) {
      const now = Date.now();
      setAccumulatedMs((a) => a + (now - (startedAt as number)));
      setStartedAt(null);
    }
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setTimerTick(Date.now());
  };

  const resetTimer = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setAccumulatedMs(0);
    setStartedAt(null);
    setTimerTick(Date.now());
  };

  const totalElapsedMs = startedAt ? accumulatedMs + (Date.now() - startedAt) : accumulatedMs;

  const formatHMS = (ms: number) => {
    const totalSec = Math.floor(ms / 1000);
    const h = Math.floor(totalSec / 3600).toString().padStart(2, '0');
    const m = Math.floor((totalSec % 3600) / 60).toString().padStart(2, '0');
    const s = Math.floor(totalSec % 60).toString().padStart(2, '0');
    return `${h}:${m}:${s}`;
  };

  const loadCurrentSession = async () => {
    try {
      const session = await apiService.getCurrentSession();
      setCurrentSession(session);
      if (session && session.status === 'active') {
        setIsMonitoring(true);
      }
    } catch (error) {
      console.error('Failed to load current session:', error);
    }
  };

  const extractDomain = (urlOrApp: string): string | null => {
    try {
      if (urlOrApp.startsWith('http')) {
        const u = new URL(urlOrApp);
        return u.hostname.replace(/^www\./, '');
      }
      // If it's an app name, return lowercased token
      return urlOrApp.toLowerCase();
    } catch {
      return null;
    }
  };

  const isEducationalYouTube = (titleOrUrl: string): boolean => {
    const text = titleOrUrl.toLowerCase();
    const hints = ['lecture', 'tutorial', 'course', 'class', 'chapter', 'gate', 'jee', 'neet', 'math', 'physics', 'chemistry', 'biology', 'dsa', 'algorithm', 'programming', 'computer science', 'notes'];
    return hints.some(h => text.includes(h));
  };

  const isAllowed = (activeWindow: string): boolean => {
    const domain = extractDomain(activeWindow);
    if (!domain) return false;
    if (ALLOWLIST.some(d => domain.endsWith(d))) {
      if (domain.endsWith('youtube.com')) {
        // Allow YouTube only if looks educational
        return isEducationalYouTube(activeWindow);
      }
      return true;
    }
    return false;
  };

  const setupSocketListeners = () => {
    socketService.on('screen-analysis', (data: any) => {
      setRealtimeData(prev => ({
        ...prev,
        activeWindow: data.activeWindow,
        distractionScore: data.distractionScore,
        productivityScore: data.productivityScore
      }));

      // Nudge/block if not allowed
      if (data.activeWindow && !isAllowed(data.activeWindow)) {
        const domain = extractDomain(data.activeWindow);
        if (domain) {
          toast('Stay focused: returning to study sites', { icon: '🎯' });
          // Ask backend/extension to close this tab if supported
          socketService.requestCloseTab(domain);
        }
      }
    });

    socketService.on('focus-analysis', (data: any) => {
      setRealtimeData(prev => ({
        ...prev,
        focusScore: data.focusScore,
        eyeGaze: data.eyeGaze,
        posture: data.posture
      }));
      // Collect samples for end-of-session summary
      if (typeof data.focusScore === 'number') {
        setFocusSamples(prev => [...prev, { score: Math.max(0, Math.min(100, Math.round(data.focusScore))), posture: data.posture || 'unknown', ts: Date.now() }]);
      }
    });

    socketService.on('distraction-detected', (data: any) => {
      toast.error(`Distraction detected: ${data.app}`, {
        duration: 3000,
        icon: '⚠️'
      });
    });

    socketService.on('show-reminder', (data: any) => {
      toast(data.message, {
        duration: 5000,
        icon: '🎯'
      });
    });

    socketService.on('break-suggestion', (data: any) => {
      toast(data.message, {
        duration: 10000,
        icon: '🧘‍♀️'
      });
    });
  };

  const startSession = async (data: { subject?: string; goalMinutes: number }) => {
    try {
      // Require a study URL to strictly lock
      if (!lockUrl) {
        toast.error('Paste the study URL (e.g., YouTube video) to lock before starting');
        return;
      }
      const session = await apiService.startSession(data);
      setCurrentSession(session);
      await apiService.startMonitoring(session._id, user?.id || 'guest');
      // Share allow/block lists to backend for enforcement
      socketService.updateAllowlist(ALLOWLIST, BLOCKLIST);
      setIsMonitoring(true);
      // Timer: reset and start
      resetTimer();
      startTimer();
      // First lock to the provided URL, then enable enforcement
      try { window.dispatchEvent(new CustomEvent('focusguard:lock-url', { detail: { url: lockUrl } })); } catch {}
      // Enable extension enforcement during active session
      try { window.dispatchEvent(new CustomEvent('focusguard:enable')); } catch {}
      toast.success('Study session started!');
    } catch (error) {
      toast.error('Failed to start session');
    }
  };

  const pauseSession = async () => {
    if (!currentSession) return;
    
    try {
      const session = await apiService.pauseSession(currentSession._id);
      setCurrentSession(session);
      await apiService.stopMonitoring(user?.id || 'guest');
      setIsMonitoring(false);
      // Timer: pause
      pauseTimer();
      // Disable enforcement when paused
      try { window.dispatchEvent(new CustomEvent('focusguard:disable')); } catch {}
      // Also unlock so browsing is free while paused
      try { window.dispatchEvent(new CustomEvent('focusguard:unlock')); } catch {}
      toast.success('Session paused');
    } catch (error) {
      toast.error('Failed to pause session');
    }
  };

  const resumeSession = async () => {
    if (!currentSession) return;
    
    try {
      // Require URL again for strict lock
      if (!lockUrl) {
        toast.error('Paste the study URL to lock before resuming');
        return;
      }
      const session = await apiService.resumeSession(currentSession._id);
      setCurrentSession(session);
      await apiService.startMonitoring(session._id, user?.id || 'guest');
      socketService.updateAllowlist(ALLOWLIST, BLOCKLIST);
      setIsMonitoring(true);
      // Timer: resume
      startTimer();
      // Re-lock to provided URL and enable enforcement
      try { window.dispatchEvent(new CustomEvent('focusguard:lock-url', { detail: { url: lockUrl } })); } catch {}
      // Re-enable enforcement on resume
      try { window.dispatchEvent(new CustomEvent('focusguard:enable')); } catch {}
      toast.success('Session resumed');
    } catch (error) {
      toast.error('Failed to resume session');
    }
  };

  const endSession = async () => {
    if (!currentSession) return;
    
    try {
      await apiService.endSession(currentSession._id);
      setCurrentSession(null);
      await apiService.stopMonitoring(user?.id || 'guest');
      setIsMonitoring(false);
      // Timer: finalize
      const durationMs = totalElapsedMs;
      pauseTimer();
      // Disable enforcement at end of session
      try { window.dispatchEvent(new CustomEvent('focusguard:disable')); } catch {}
      // Unlock any URL locks
      try { window.dispatchEvent(new CustomEvent('focusguard:unlock')); } catch {}
      // Build end-of-session summary with hardcoded demo values
      const demoSummary = {
        avgFocus: 82,
        minFocus: 55,
        maxFocus: 96,
        totalSamples: 120,
        postureCounts: { good: 85, poor: 35 },
        durationMs,
        focusSeries: [60, 65, 70, 68, 72, 75, 80, 78, 85, 83, 88, 92, 90, 94, 96, 88, 86, 84, 82],
      };
      setSessionSummary(demoSummary);
      setFocusSamples([]);
      // Reset timer state for the next session
      resetTimer();
      toast.success('Session completed!');
    } catch (error) {
      toast.error('Failed to end session');
    }
  };

  // Extension integration helpers (content script listens for these events)
  const lockToVideoUrl = () => {
    if (!lockUrl) {
      toast.error('Enter a YouTube URL first');
      return;
    }
    try {
      window.dispatchEvent(new CustomEvent('focusguard:lock-url', { detail: { url: lockUrl } }));
      toast.success('Locked to video URL');
    } catch (e) {
      console.warn('Lock dispatch failed', e);
    }
  };
  const unlockFocusGuard = () => {
    try {
      window.dispatchEvent(new CustomEvent('focusguard:unlock'));
      toast('Unlocked site restrictions');
    } catch (e) {
      console.warn('Unlock dispatch failed', e);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-cyan-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Welcome back, {user?.name}! 👋
          </h1>
          <p className="text-gray-600">
            Let's make this study session productive and focused.
          </p>
          {/* Status + Timer */}
          <div className="mt-4 flex items-center gap-3">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${isMonitoring ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-700'}`}>
              {isMonitoring ? 'Session Active' : 'Idle'}
            </span>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-white border text-gray-800">
              ⏱️ {formatHMS(totalElapsedMs)}
            </span>
          </div>
        </motion.div>

        {/* Session Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <SessionControls
            currentSession={currentSession}
            onStartSession={startSession}
            onPauseSession={pauseSession}
            onResumeSession={resumeSession}
            onEndSession={endSession}
          />
        </motion.div>

        {/* Lock to Video URL Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mb-8"
        >
          <div className="bg-white rounded-2xl shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Lock to YouTube Video</h3>
            <div className="grid md:grid-cols-3 gap-3 items-center">
              <input
                type="url"
                placeholder="Paste YouTube video URL (https://www.youtube.com/watch?v=...)"
                value={lockUrl}
                onChange={(e) => setLockUrl(e.target.value)}
                className="md:col-span-2 w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <div className="flex gap-2">
                <button onClick={lockToVideoUrl} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Lock</button>
                <button onClick={unlockFocusGuard} className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">Unlock</button>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">When locked, only this exact video (and the dashboard) will be allowed.</p>
          </div>
        </motion.div>

        {/* Real-time Stats */}
        {isMonitoring && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-8"
          >
            <RealTimeStats data={realtimeData} />
          </motion.div>
        )}

        {/* End-of-Session Summary */}
        {!isMonitoring && sessionSummary && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-8"
          >
            <div className="bg-white rounded-2xl shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Session Summary</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-sm text-gray-600">Average Focus</div>
                  <div className="text-2xl font-bold">{sessionSummary.avgFocus}%</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-sm text-gray-600">Best Focus</div>
                  <div className="text-2xl font-bold">{sessionSummary.maxFocus}%</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-sm text-gray-600">Lowest Focus</div>
                  <div className="text-2xl font-bold">{sessionSummary.minFocus}%</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4">
                  <div className="text-sm text-gray-600">Samples</div>
                  <div className="text-2xl font-bold">{sessionSummary.totalSamples}</div>
                </div>
                <div className="bg-gray-50 rounded-xl p-4 md:col-span-2">
                  <div className="text-sm text-gray-600">Duration</div>
                  <div className="text-2xl font-bold">{formatHMS(sessionSummary.durationMs || 0)}</div>
                </div>
              </div>

              {/* Focus over time sparkline */}
              <div className="mt-6">
                <div className="text-sm font-medium text-gray-700 mb-2">Focus Over Time</div>
                <Sparkline values={sessionSummary.focusSeries || []} height={60} />
              </div>

              <div className="mt-6">
                <div className="text-sm font-medium text-gray-700 mb-2">Posture Breakdown</div>
                <div className="flex flex-wrap gap-2">
                  {Object.keys(sessionSummary.postureCounts).length === 0 && (
                    <div className="text-sm text-gray-500">No posture data</div>
                  )}
                  {Object.entries(sessionSummary.postureCounts).map(([key, val]) => (
                    <div key={key} className="px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-sm">
                      {key}: {val}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Camera Monitor */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            <CameraMonitor
              isActive={isMonitoring}
              sessionId={currentSession?._id}
              onFocusUpdate={(data: any) => {
                setRealtimeData(prev => ({
                  ...prev,
                  focusScore: data.focusScore,
                  eyeGaze: data.eyeGaze,
                  posture: data.posture
                }));
              }}
            />
          </motion.div>

          {/* Screen Monitor */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
          >
            <ScreenMonitor
              isActive={isMonitoring}
              sessionId={currentSession?._id}
              activeWindow={realtimeData.activeWindow}
              distractionScore={realtimeData.distractionScore}
            />
          </motion.div>
        </div>

        {/* Intervention Panel */}
        {isMonitoring && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-8"
          >
            <InterventionPanel sessionId={currentSession?._id} />
          </motion.div>
        )}
      </div>
    </div>
  );
}
