import { useCallback } from 'react';
import { useLiveVoice, type ConnectionStatus } from './hooks/useLiveVoice';

const STATUS_CONFIG: Record<ConnectionStatus, { label: string; color: string; dot: string }> = {
  idle: { label: 'Offline', color: 'text-gray-400', dot: 'bg-gray-500' },
  connecting: { label: 'Connecting…', color: 'text-yellow-400', dot: 'bg-yellow-400 animate-pulse' },
  connected: { label: 'Connected', color: 'text-emerald-400', dot: 'bg-emerald-400' },
  error: { label: 'Error', color: 'text-red-400', dot: 'bg-red-500' },
};

function WaveformBars() {
  return (
    <div className="flex items-center gap-[3px] h-8">
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className="wave-bar w-[3px] rounded-full bg-indigo-400"
          style={{ animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  );
}

export default function App() {
  const { status, isRecording, toolEvent, startRecording, stopRecording } = useLiveVoice();
  const cfg = STATUS_CONFIG[status];

  // Toggle function instead of push-to-talk
  const handleToggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-10 px-4"
      style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(99,102,241,0.12) 0%, #0a0d14 65%)' }}>

      {/* Header */}
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-white">
          Repo<span className="text-indigo-400">Recon</span>
        </h1>
        <p className="mt-2 text-sm text-gray-500 tracking-widest uppercase">
          Live Voice Bridge — Phase 1 Echo Test
        </p>
      </div>

      {/* Status pill */}
      <div className="flex items-center gap-2 px-4 py-2 rounded-full border border-gray-800 bg-gray-900/60 backdrop-blur">
        <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
        <span className={`text-sm font-medium ${cfg.color}`}>{cfg.label}</span>
      </div>

      {/* Visual Tactical Dashboard */}
      <div className="w-full max-w-md min-h-[120px] rounded-xl border border-gray-800 bg-gray-900/50 p-6 flex flex-col items-center justify-center transition-all duration-300 relative overflow-hidden">
        {toolEvent ? (
          <>
            <div className="absolute inset-0 border-2 border-indigo-500 rounded-xl animate-pulse opacity-50 pointer-events-none" />
            <div className="flex items-center gap-3 mb-2">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
              </span>
              <h2 className="text-sm font-semibold text-indigo-400 tracking-widest uppercase">
                Agent Executing Protocol
              </h2>
            </div>
            <div className="text-center">
              <div className="text-xl font-mono text-white mb-1">{toolEvent.function}</div>
              {toolEvent.arguments?.repo_name && (
                <div className="text-sm font-mono text-gray-400">Target: {toolEvent.arguments.repo_name}</div>
              )}
            </div>
          </>
        ) : (
          <div className="text-sm font-medium text-gray-600 tracking-widest uppercase">
            Awaiting voice commands...
          </div>
        )}
      </div>

      {/* Tap-to-talk button */}
      <div className="relative flex items-center justify-center">
        {/* Animated glow ring when recording */}
        {isRecording && (
          <span className="pulse-ring absolute w-28 h-28 rounded-full border-2 border-indigo-500 opacity-70 pointer-events-none" />
        )}

        <button
          onClick={handleToggleRecording}
          className={`
            w-24 h-24 rounded-full flex flex-col items-center justify-center gap-2
            font-semibold text-xs tracking-widest uppercase
            select-none touch-none transition-all duration-150
            border-2 shadow-lg cursor-pointer
            ${isRecording
              ? 'bg-indigo-600 border-indigo-400 scale-95 shadow-indigo-500/40 text-white'
              : 'bg-gray-900 border-gray-700 hover:border-indigo-500 hover:bg-gray-800 text-gray-300 hover:text-white'}
          `}
          aria-label={isRecording ? "Tap to stop" : "Tap to speak"}
        >
          {isRecording ? (
            <>
              <WaveformBars />
              <span>Stop</span>
            </>
          ) : (
            <>
              {/* Mic icon */}
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="2" width="6" height="13" rx="3" />
                <path d="M5 10a7 7 0 0 0 14 0" />
                <line x1="12" y1="19" x2="12" y2="22" />
                <line x1="8" y1="22" x2="16" y2="22" />
              </svg>
              <span>Speak</span>
            </>
          )}
        </button>
      </div>

      {/* Footer hint */}
      <p className="text-xs text-gray-600 text-center max-w-xs leading-relaxed">
        Tap the button to start the live agent.<br />
        Tap again to disconnect.
      </p>
    </div>
  );
}