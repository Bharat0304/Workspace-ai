import React from 'react';
import { Gauge, Target, Zap } from 'lucide-react';

interface Props {
  data: {
    focusScore: number;
    distractionScore: number; // 0-1 from backend; we'll scale to %
    productivityScore: number;
    eyeGaze: string;
    posture: string;
    activeWindow: string;
  };
}

function barColor(v: number) {
  if (v >= 80) return 'from-emerald-500 to-teal-500';
  if (v >= 60) return 'from-yellow-500 to-amber-500';
  return 'from-rose-500 to-pink-500';
}

export function RealTimeStats({ data }: Props) {
  const focus = Math.max(0, Math.min(100, Math.round(data.focusScore || 0)));
  const productivity = Math.max(0, Math.min(100, Math.round(data.productivityScore || 0)));
  const distractionPct = Math.max(0, Math.min(100, Math.round((data.distractionScore || 0) * 100)));

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Focus */}
      <div className="rounded-2xl p-5 bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-100 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-medium text-gray-700">Focus</div>
          <Gauge className="h-5 w-5 text-indigo-600" />
        </div>
        <div className="text-3xl font-bold text-gray-900">{focus}%</div>
        <div className="w-full bg-white/70 rounded-full h-2 mt-3 overflow-hidden">
          <div className={`h-2 rounded-full bg-gradient-to-r ${barColor(focus)}`} style={{ width: `${focus}%` }} />
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
          <span>Eye: {data.eyeGaze || '—'}</span>
          <span>Posture: {data.posture || '—'}</span>
        </div>
      </div>

      {/* Productivity */}
      <div className="rounded-2xl p-5 bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-medium text-gray-700">Productivity</div>
          <Zap className="h-5 w-5 text-emerald-600" />
        </div>
        <div className="text-3xl font-bold text-gray-900">{productivity}%</div>
        <div className="w-full bg-white/70 rounded-full h-2 mt-3 overflow-hidden">
          <div className={`h-2 rounded-full bg-gradient-to-r ${barColor(productivity)}`} style={{ width: `${productivity}%` }} />
        </div>
        <div className="mt-3 text-xs text-gray-500 truncate">Active window: {data.activeWindow || '—'}</div>
      </div>

      {/* Distraction */}
      <div className="rounded-2xl p-5 bg-gradient-to-br from-rose-50 to-pink-50 border border-rose-100 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-medium text-gray-700">Distraction Risk</div>
          <Target className="h-5 w-5 text-rose-600" />
        </div>
        <div className="text-3xl font-bold text-gray-900">{distractionPct}%</div>
        <div className="w-full bg-white/70 rounded-full h-2 mt-3 overflow-hidden">
          <div className={`h-2 rounded-full bg-gradient-to-r ${barColor(100 - distractionPct)}`} style={{ width: `${distractionPct}%` }} />
        </div>
        <div className="mt-3 text-xs text-gray-500">Lower is better</div>
      </div>
    </div>
  );
}
