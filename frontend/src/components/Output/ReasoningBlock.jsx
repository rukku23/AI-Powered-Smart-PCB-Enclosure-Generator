/**
 * EnclosureAI — Reasoning Block Display
 * Collapsible panel with syntax-highlighted AI design reasoning.
 * Section-based color coding: GEOMETRY=cyan, THERMAL=amber, MATERIAL=green, FEATURES=purple
 */
import { useState } from 'react'

const SECTION_COLORS = {
  GEOMETRY: 'text-cyan-400',
  THERMAL: 'text-amber-400',
  MATERIAL: 'text-green-400',
  FEATURES: 'text-purple-400',
  DESIGN: 'text-cyan-300',
}

function highlightLine(line) {
  // Check if line starts with a section keyword
  for (const [keyword, colorClass] of Object.entries(SECTION_COLORS)) {
    if (line.trimStart().startsWith(keyword)) {
      return <span className={`${colorClass} font-semibold`}>{line}</span>
    }
  }

  // Section separator lines
  if (line.match(/^[=\-─━]{3,}/)) {
    return <span className="text-zinc-700">{line}</span>
  }

  // Comment-style lines
  if (line.trimStart().startsWith('//') || line.trimStart().startsWith('*')) {
    return <span className="text-zinc-600">{line}</span>
  }

  return <span className="text-zinc-400">{line}</span>
}

export default function ReasoningBlock({ reasoning }) {
  const [expanded, setExpanded] = useState(true)
  const [copied, setCopied] = useState(false)

  if (!reasoning) return null

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(reasoning)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback
      const ta = document.createElement('textarea')
      ta.value = reasoning
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const lines = reasoning.split('\n')

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-zinc-800/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <span className={`text-xs transition-transform ${expanded ? 'rotate-90' : ''}`}>▸</span>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
            AI Design Reasoning
          </h3>
          <span className="text-[10px] text-zinc-700">{lines.length} lines</span>
        </div>

        <button
          onClick={(e) => { e.stopPropagation(); handleCopy() }}
          className="px-2 py-1 rounded text-[10px] text-zinc-500 hover:text-zinc-300
            hover:bg-zinc-800 transition-colors"
          title="Copy to clipboard"
        >
          {copied ? '✓ Copied' : '📋 Copy'}
        </button>
      </div>

      {/* Content */}
      {expanded && (
        <div className="border-t border-zinc-800">
          <pre className="px-4 py-3 text-[11px] font-mono leading-relaxed
            max-h-80 overflow-y-auto whitespace-pre-wrap break-words">
            {lines.map((line, i) => (
              <div key={i}>{highlightLine(line)}</div>
            ))}
          </pre>
        </div>
      )}
    </div>
  )
}
