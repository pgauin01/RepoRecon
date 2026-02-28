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
  const { status, isRecording, startRecording, stopRecording } = useLiveVoice();
  const cfg = STATUS_CONFIG[status];

  const handlePointerDown = useCallback(() => {
    startRecording();
  }, [startRecording]);

  const handlePointerUp = useCallback(() => {
    stopRecording();
  }, [stopRecording]);

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

      {/* Push-to-talk button */}
      <div className="relative flex items-center justify-center">
        {/* Animated glow ring when recording */}
        {isRecording && (
          <span className="pulse-ring absolute w-28 h-28 rounded-full border-2 border-indigo-500 opacity-70 pointer-events-none" />
        )}

        <button
          onPointerDown={handlePointerDown}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}   // safety: release if cursor leaves
          className={`
            w-24 h-24 rounded-full flex flex-col items-center justify-center gap-2
            font-semibold text-xs tracking-widest uppercase
            select-none touch-none transition-all duration-150
            border-2 shadow-lg
            ${isRecording
              ? 'bg-indigo-600 border-indigo-400 scale-95 shadow-indigo-500/40 text-white'
              : 'bg-gray-900 border-gray-700 hover:border-indigo-500 hover:bg-gray-800 text-gray-300 hover:text-white'}
          `}
          aria-label="Hold to speak"
        >
          {isRecording ? (
            <>
              <WaveformBars />
              <span>Speaking</span>
            </>
          ) : (
            <>
              {/* Mic icon (inline SVG — no external dep needed) */}
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="2" width="6" height="13" rx="3" />
                <path d="M5 10a7 7 0 0 0 14 0" />
                <line x1="12" y1="19" x2="12" y2="22" />
                <line x1="8" y1="22" x2="16" y2="22" />
              </svg>
              <span>Hold</span>
            </>
          )}
        </button>
      </div>

      {/* Footer hint */}
      <p className="text-xs text-gray-600 text-center max-w-xs leading-relaxed">
        Hold the button to stream raw PCM audio to the echo backend.<br />
        You should hear your voice played back with minimal latency.
      </p>
    </div>
  );
}
