/**
 * EnclosureAI — PCB Dimensions Panel
 * Numeric inputs for PCB dimensions with real-time validation
 * and live enclosure size preview.
 */
import { useState } from 'react'

function NumericInput({ label, unit, value, onChange, min, max, step, required, error }) {
  return (
    <div>
      <label className="block text-xs text-zinc-400 mb-1">{label}</label>
      <div className="relative">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          min={min}
          max={max}
          step={step || 0.1}
          required={required}
          className={`w-full px-3 py-2 pr-10 rounded-lg text-sm
            bg-zinc-800 border transition-colors
            ${error
              ? 'border-red-500 focus:ring-red-500/30'
              : 'border-zinc-700 focus:border-cyan-500 focus:ring-cyan-500/20'
            }
            text-zinc-100 placeholder-zinc-600
            focus:outline-none focus:ring-2`}
          placeholder={`${min}–${max}`}
        />
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-500">
          {unit}
        </span>
      </div>
      {error && <p className="text-[10px] text-red-400 mt-0.5">{error}</p>}
    </div>
  )
}

export default function PCBDimensionsPanel({ formData, onChange }) {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const pcb = formData.pcb

  const updatePcb = (field, value) => {
    onChange({
      ...formData,
      pcb: { ...formData.pcb, [field]: value },
    })
  }

  // Validation
  const lengthVal = parseFloat(pcb.length)
  const widthVal = parseFloat(pcb.width)
  const lengthError = pcb.length !== '' && (lengthVal < 10 || lengthVal > 500)
    ? 'Must be 10–500mm' : null
  const widthError = pcb.width !== '' && (widthVal < 10 || widthVal > 500)
    ? 'Must be 10–500mm' : null

  // Live preview
  const hasValidDims = !lengthError && !widthError && pcb.length && pcb.width
  const approxLength = hasValidDims ? (lengthVal + 8.4).toFixed(1) : '—'
  const approxWidth = hasValidDims ? (widthVal + 8.4).toFixed(1) : '—'

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
        PCB Dimensions
      </h3>

      <div className="grid grid-cols-2 gap-3">
        <NumericInput
          label="Length" unit="mm"
          value={pcb.length} onChange={(v) => updatePcb('length', v)}
          min={10} max={500} required error={lengthError}
        />
        <NumericInput
          label="Width" unit="mm"
          value={pcb.width} onChange={(v) => updatePcb('width', v)}
          min={10} max={500} required error={widthError}
        />
      </div>

      {/* Live enclosure preview */}
      {hasValidDims && (
        <div className="mt-2 px-3 py-1.5 rounded-md bg-zinc-800/60 border border-zinc-700/50">
          <p className="text-[11px] text-zinc-400">
            Enclosure ≈ <span className="text-cyan-400 font-medium">{approxLength}</span> × <span className="text-cyan-400 font-medium">{approxWidth}</span> mm
          </p>
        </div>
      )}

      {/* Advanced section */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="mt-3 text-[11px] text-zinc-500 hover:text-zinc-400 transition-colors flex items-center gap-1"
      >
        <span className={`transition-transform ${showAdvanced ? 'rotate-90' : ''}`}>▸</span>
        Advanced
      </button>

      {showAdvanced && (
        <div className="grid grid-cols-2 gap-3 mt-2">
          <NumericInput
            label="Thickness" unit="mm"
            value={pcb.thickness} onChange={(v) => updatePcb('thickness', v)}
            min={0.4} max={5} step={0.1}
          />
          <NumericInput
            label="Hole Ø" unit="mm"
            value={pcb.mounting_hole_diameter}
            onChange={(v) => updatePcb('mounting_hole_diameter', v)}
            min={1.5} max={6} step={0.1}
          />
        </div>
      )}
    </div>
  )
}
