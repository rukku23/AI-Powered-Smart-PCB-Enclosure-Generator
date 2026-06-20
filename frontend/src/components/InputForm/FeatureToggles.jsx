/**
 * EnclosureAI — Feature Toggles (Phase 8)
 * Material, print tech, lid style, ventilation, display window, aesthetic style,
 * and Design Context section with live strategy preview.
 */
import { useState, useEffect, useCallback } from 'react'
import { predictStrategy } from '../../api/client'

const MATERIALS = [
  { value: 'PLA', label: 'PLA', tooltip: 'Tg 60°C · Easy to print · Low heat resistance' },
  { value: 'PETG', label: 'PETG', tooltip: 'Tg 80°C · Good chemical resistance · Flexible' },
  { value: 'ABS', label: 'ABS', tooltip: 'Tg 105°C · Impact resistant · Needs enclosure' },
  { value: 'ASA', label: 'ASA', tooltip: 'Tg 100°C · UV resistant · Outdoor use' },
  { value: 'PC', label: 'PC', tooltip: 'Tg 147°C · High temp · Very strong' },
  { value: 'SLA_STANDARD', label: 'SLA Standard', tooltip: 'Tg 55°C · High detail · Brittle' },
  { value: 'SLA_TOUGH', label: 'SLA Tough', tooltip: 'Tg 65°C · Impact resistant resin' },
]

const PRINT_TECH = ['FDM', 'SLA', 'SLS']
const LID_STYLES = [
  { value: 'SNAP_FIT', label: 'Snap-Fit' },
  { value: 'SCREWED_M2', label: 'Screwed M2' },
  { value: 'SCREWED_M3', label: 'Screwed M3' },
  { value: 'SLIDE', label: 'Slide' },
]
const AESTHETICS = ['MINIMAL', 'INDUSTRIAL', 'CONSUMER', 'ROUNDED', 'WEARABLE']

const USE_CASES = [
  { value: 'BENCH_PROTOTYPE', label: 'Bench prototype' },
  { value: 'IOT_DEVICE', label: 'IoT device' },
  { value: 'INDUSTRIAL_CONTROLLER', label: 'Industrial controller' },
  { value: 'CONSUMER_PRODUCT', label: 'Consumer product' },
  { value: 'WEARABLE', label: 'Wearable' },
  { value: 'SCIENTIFIC_INSTRUMENT', label: 'Scientific instrument' },
]

const ACCESS_FREQ = [
  { value: 'RARELY', label: 'Opened rarely' },
  { value: 'MONTHLY', label: 'Monthly' },
  { value: 'WEEKLY', label: 'Weekly' },
  { value: 'DAILY', label: 'Daily' },
]

const MOUNTINGS = [
  { value: 'DESKTOP', label: 'Desktop' },
  { value: 'WALL_MOUNT', label: 'Wall mount' },
  { value: 'DIN_RAIL', label: 'DIN rail' },
  { value: 'PANEL_CUTOUT', label: 'Panel cutout' },
  { value: 'HANDHELD', label: 'Handheld' },
  { value: 'WEARABLE', label: 'Wearable' },
]

const ENVIRONMENTS = [
  { value: 'INDOOR', label: 'Indoor (normal)' },
  { value: 'INDOOR_INDUSTRIAL', label: 'Indoor (industrial)' },
  { value: 'OUTDOOR', label: 'Outdoor' },
  { value: 'WET_HUMID', label: 'Wet / humid' },
]

const STRATEGY_COLORS = {
  RECTANGULAR_FLAT_LID: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
  RECTANGULAR_RIBBED_LID: 'text-cyan-300 bg-cyan-500/10 border-cyan-500/30',
  CLAMSHELL_HORIZONTAL: 'text-green-400 bg-green-500/10 border-green-500/30',
  CLAMSHELL_VERTICAL: 'text-green-300 bg-green-500/10 border-green-500/30',
  INDUSTRIAL_FLANGED: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  DIN_RAIL_CLIP: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  WEARABLE_ROUNDED: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
  CHIMNEY_THERMAL: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  THREE_PIECE_ACCESS: 'text-teal-400 bg-teal-500/10 border-teal-500/30',
  PANEL_MOUNT_BEZEL: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
  SEALED_IP_RATED: 'text-red-400 bg-red-500/10 border-red-500/30',
  SNAP_RAIL_MODULAR: 'text-pink-400 bg-pink-500/10 border-pink-500/30',
}

function PillGroup({ options, value, onChange, labelKey = 'label', valueKey = 'value' }) {
  const items = typeof options[0] === 'string'
    ? options.map(o => ({ label: o, value: o }))
    : options.map(o => ({ label: o[labelKey], value: o[valueKey] }))

  return (
    <div className="flex flex-wrap gap-1">
      {items.map(o => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={`px-3 py-1.5 rounded-md text-[11px] font-medium transition-all
            ${value === o.value
              ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/40'
              : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:text-zinc-200 hover:border-zinc-600'
            }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="flex items-center justify-between cursor-pointer group">
      <span className="text-xs text-zinc-400 group-hover:text-zinc-300">{label}</span>
      <div
        onClick={() => onChange(!checked)}
        className={`relative w-9 h-5 rounded-full transition-colors cursor-pointer
          ${checked ? 'bg-cyan-500' : 'bg-zinc-700'}`}
      >
        <div className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform shadow
          ${checked ? 'translate-x-4' : 'translate-x-0'}`}
        />
      </div>
    </label>
  )
}

function DropdownSelect({ label, value, onChange, options }) {
  return (
    <div>
      <label className="block text-xs text-zinc-400 mb-1.5">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 rounded-lg text-sm bg-zinc-800 border border-zinc-700
          text-zinc-200 focus:border-cyan-500 focus:outline-none appearance-none"
      >
        {options.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  )
}

export default function FeatureToggles({ formData, onChange }) {
  const update = (field, value) => onChange({ ...formData, [field]: value })
  const updateContext = (field, value) => {
    const ctx = { ...(formData.design_context || {}), [field]: value }
    onChange({ ...formData, design_context: ctx })
  }

  const activeMaterial = MATERIALS.find(m => m.value === formData.material)
  const ctx = formData.design_context || {}

  // Strategy preview state
  const [prediction, setPrediction] = useState(null)
  const [contextOpen, setContextOpen] = useState(false)

  // Debounced strategy prediction
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const result = await predictStrategy({
          use_case: ctx.use_case || 'BENCH_PROTOTYPE',
          access_frequency: ctx.access_frequency || 'RARELY',
          mounting: ctx.mounting || 'DESKTOP',
          environment: ctx.environment || 'INDOOR',
        })
        setPrediction(result)
      } catch { /* ignore prediction errors */ }
    }, 300)
    return () => clearTimeout(timer)
  }, [ctx.use_case, ctx.access_frequency, ctx.mounting, ctx.environment])

  const strategyColors = prediction
    ? STRATEGY_COLORS[prediction.strategy] || 'text-zinc-400 bg-zinc-800 border-zinc-700'
    : ''

  return (
    <div className="space-y-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
        Configuration
      </h3>

      {/* Material */}
      <div>
        <label className="block text-xs text-zinc-400 mb-1.5">Material</label>
        <select
          value={formData.material}
          onChange={(e) => update('material', e.target.value)}
          className="w-full px-3 py-2 rounded-lg text-sm bg-zinc-800 border border-zinc-700
            text-zinc-200 focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20
            appearance-none"
        >
          {MATERIALS.map(m => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
        {activeMaterial && (
          <p className="text-[10px] text-zinc-500 mt-1">{activeMaterial.tooltip}</p>
        )}
      </div>

      {/* Print Technology */}
      <div>
        <label className="block text-xs text-zinc-400 mb-1.5">Print Technology</label>
        <PillGroup
          options={PRINT_TECH}
          value={formData.print_technology}
          onChange={(v) => update('print_technology', v)}
        />
      </div>

      {/* Lid Style */}
      <div>
        <label className="block text-xs text-zinc-400 mb-1.5">Lid Style</label>
        <PillGroup
          options={LID_STYLES}
          value={formData.lid_style}
          onChange={(v) => update('lid_style', v)}
        />
      </div>

      {/* Aesthetic */}
      <div>
        <label className="block text-xs text-zinc-400 mb-1.5">Aesthetic Style</label>
        <select
          value={formData.aesthetic_style}
          onChange={(e) => update('aesthetic_style', e.target.value)}
          className="w-full px-3 py-2 rounded-lg text-sm bg-zinc-800 border border-zinc-700
            text-zinc-200 focus:border-cyan-500 focus:outline-none appearance-none"
        >
          {AESTHETICS.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>

      {/* Toggles */}
      <div className="space-y-3 pt-1">
        <Toggle
          label="Ventilation Slots"
          checked={formData.ventilation}
          onChange={(v) => update('ventilation', v)}
        />
        <Toggle
          label="Display Window"
          checked={formData.display_window}
          onChange={(v) => update('display_window', v)}
        />
      </div>

      {/* ═══ Design Context (Phase 8) ═══════════════════════════ */}
      <div className="border border-zinc-700/50 rounded-lg overflow-hidden">
        <button
          onClick={() => setContextOpen(!contextOpen)}
          className="w-full flex items-center justify-between px-3 py-2.5
            text-xs font-semibold uppercase tracking-wider text-zinc-400
            hover:text-zinc-200 transition-colors bg-zinc-800/50"
        >
          <span className="flex items-center gap-2">
            🎯 Design Context
          </span>
          <span className={`transition-transform ${contextOpen ? 'rotate-180' : ''}`}>▾</span>
        </button>

        {contextOpen && (
          <div className="p-3 space-y-3 border-t border-zinc-700/50 bg-zinc-900/30">
            <DropdownSelect
              label="Use Case"
              value={ctx.use_case || 'BENCH_PROTOTYPE'}
              onChange={(v) => updateContext('use_case', v)}
              options={USE_CASES}
            />
            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">Access Frequency</label>
              <PillGroup
                options={ACCESS_FREQ}
                value={ctx.access_frequency || 'RARELY'}
                onChange={(v) => updateContext('access_frequency', v)}
              />
            </div>
            <DropdownSelect
              label="Mounting"
              value={ctx.mounting || 'DESKTOP'}
              onChange={(v) => updateContext('mounting', v)}
              options={MOUNTINGS}
            />
            <DropdownSelect
              label="Environment"
              value={ctx.environment || 'INDOOR'}
              onChange={(v) => updateContext('environment', v)}
              options={ENVIRONMENTS}
            />
          </div>
        )}

        {/* Strategy Preview */}
        {prediction && (
          <div className={`px-3 py-2 border-t border-zinc-700/30 flex items-center gap-2`}>
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px]
              font-semibold border ${strategyColors}`}>
              {prediction.display_name}
            </span>
            <span className="text-[10px] text-zinc-500 truncate">
              {prediction.reason}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
