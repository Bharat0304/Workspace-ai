import React, { useMemo, useState } from 'react';

type Props = {
  currentSession: {
    _id: string;
    subject?: string;
    goalMinutes?: number;
    status: 'active' | 'paused' | 'completed';
  } | null;
  onStartSession: (data: { subject?: string; goalMinutes: number }) => void;
  onPauseSession: () => void;
  onResumeSession: () => void;
  onEndSession: () => void;
};

export function SessionControls({ currentSession, onStartSession, onPauseSession, onResumeSession, onEndSession }: Props) {
  const [subject, setSubject] = useState('');
  const [goalMinutes, setGoalMinutes] = useState(60);

  const isActive = currentSession?.status === 'active';
  const isPaused = currentSession?.status === 'paused';

  const canStart = useMemo(() => goalMinutes >= 1 && goalMinutes <= 480, [goalMinutes]);

  if (!currentSession) {
    return (
      <div className="bg-white rounded-2xl shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Start a Study Session</h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-2">Subject (optional)</label>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="e.g., Mathematics, Physics"
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-2">Goal (minutes)</label>
            <input
              type="number"
              min={1}
              max={480}
              value={goalMinutes}
              onChange={(e) => setGoalMinutes(parseInt(e.target.value || '0', 10))}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
        <div className="mt-4">
          <button
            disabled={!canStart}
            onClick={() => onStartSession({ subject: subject || undefined, goalMinutes })}
            className="inline-flex items-center px-5 py-2.5 bg-indigo-600 text-white rounded-lg disabled:opacity-50 hover:bg-indigo-700"
          >
            Start Session
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-sm text-gray-500">Current Session</div>
          <div className="text-lg font-semibold text-gray-900">{currentSession.subject || 'Untitled'}</div>
        </div>
        <div className={`px-3 py-1 rounded-full text-xs font-medium ${isActive ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
          {currentSession.status}
        </div>
      </div>
      <div className="flex gap-3">
        {isActive ? (
          <button onClick={onPauseSession} className="flex-1 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600">Pause</button>
        ) : (
          <button onClick={onResumeSession} className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">Resume</button>
        )}
        <button onClick={onEndSession} className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">End</button>
      </div>
    </div>
  );
}

export default SessionControls;
