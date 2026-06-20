/**
 * EnclosureAI — Progress Stream Display
 * Shows generation status with animated spinner and live reasoning text.
 */

const STATUS_CONFIG = {
  idle: { icon: null, message: null, color: '' },
  validating: { icon: '⚙️', message: 'Validating parameters...', color: 'text-zinc-400' },
  strategy_selecting: { icon: '🎯', message: 'Selecting design strategy...', color: 'text-cyan-400' },
  generating: { icon: null, message: 'AI writing enclosure code...', color: 'text-cyan-400', spin: true },
  rendering: { icon: null, message: 'Compiling OpenSCAD geometry...', color: 'text-cyan-400', spin: true },
  correcting: { icon: '🔧', message: 'Self-correcting', color: 'text-amber-400' },
  complete: { icon: '✓', message: 'Enclosure generated', color: 'text-green-400' },
  error: { icon: '✕', message: 'Generation failed', color: 'text-red-400' },
}

function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  )
}

export default function ProgressStream({ status, reasoning, attempt, error }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.idle

  if (status === 'idle') return null

  return (
    <div className="space-y-3">
      {/* Status bar */}
      <div className={`flex items-center gap-2.5 px-4 py-3 rounded-lg border
        ${status === 'error' ? 'border-red-800/50 bg-red-500/5' :
          status === 'complete' ? 'border-green-800/50 bg-green-500/5' :
          'border-zinc-700/50 bg-zinc-800/30'}`}
      >
        {config.spin ? <Spinner /> : (
          <span className="text-sm">{config.icon}</span>
        )}
        <div className="flex-1">
          <p className={`text-xs font-medium ${config.color}`}>
            {status === 'correcting'
              ? `Self-correcting: ${error || '...'} (attempt ${attempt}/3)`
              : status === 'complete'
              ? `${config.message} ✓`
              : config.message
            }
          </p>
          {(status === 'generating' || status === 'rendering') && attempt > 1 && (
            <p className="text-[10px] text-zinc-500 mt-0.5">Attempt {attempt}/3</p>
          )}
        </div>
      </div>

      {/* Error detail */}
      {status === 'error' && error && (
        <div className="px-4 py-2.5 rounded-lg border border-red-800/30 bg-red-500/5">
          <p className="text-[11px] text-red-300">{error}</p>
        </div>
      )}

      {/* Live reasoning stream */}
      {reasoning && (status === 'generating' || status === 'rendering' || status === 'complete') && (
        <div className="rounded-lg border border-zinc-700/50 bg-zinc-900 overflow-hidden">
          <div className="px-3 py-1.5 border-b border-zinc-800 flex items-center gap-2">
            <span className="text-[10px] text-zinc-500 font-medium uppercase tracking-wider">
              AI Design Reasoning
            </span>
            {status !== 'complete' && (
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            )}
          </div>
          <pre className="px-3 py-2.5 text-[11px] text-zinc-400 font-mono leading-relaxed
            max-h-48 overflow-y-auto whitespace-pre-wrap break-words">
            {reasoning}
          </pre>
        </div>
      )}
    </div>
  )
}
