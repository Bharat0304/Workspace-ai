import React from 'react';

export function InterventionPanel({ sessionId }: { sessionId?: string }) {
  return (
    <div className="bg-white rounded-2xl shadow-xl p-6">
      <h3 className="text-lg font-semibold mb-2">Interventions</h3>
      <p className="text-gray-600 text-sm">Real-time suggestions and actions will appear here.</p>
    </div>
  );
}
