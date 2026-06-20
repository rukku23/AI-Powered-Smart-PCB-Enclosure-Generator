/**
 * EnclosureAI — Component Editor
 * Dynamic list of PCB components with type-specific fields.
 * Includes quick-add buttons for common connectors.
 */

const COMPONENT_TYPES = ['CONNECTOR', 'DISPLAY', 'BUTTON', 'HEATSINK', 'ANTENNA', 'GENERIC']
const FACE_OPTIONS = ['NONE', 'FRONT', 'BACK', 'LEFT', 'RIGHT', 'TOP']

const QUICK_ADD = {
  'USB-C': {
    type: 'CONNECTOR', label: 'USB-C', position_x: 0, position_y: 0, height: 3.5,
    wattage: 0, face_access: 'FRONT', connector_width: 9, connector_height: 3.5,
  },
  'Barrel Jack': {
    type: 'CONNECTOR', label: 'Barrel Jack', position_x: 0, position_y: 0, height: 11,
    wattage: 0, face_access: 'LEFT', connector_width: 9, connector_height: 11,
  },
  'HDMI': {
    type: 'CONNECTOR', label: 'HDMI', position_x: 0, position_y: 0, height: 6.5,
    wattage: 0, face_access: 'FRONT', connector_width: 15.5, connector_height: 6.5,
  },
}

function MiniInput({ value, onChange, placeholder, className = '' }) {
  return (
    <input
      type="number"
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      step="0.1"
      className={`w-full px-2 py-1.5 rounded text-xs bg-zinc-800 border border-zinc-700
        text-zinc-200 placeholder-zinc-600 focus:border-cyan-500 focus:outline-none ${className}`}
    />
  )
}

function MiniSelect({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-2 py-1.5 rounded text-xs bg-zinc-800 border border-zinc-700
        text-zinc-200 focus:border-cyan-500 focus:outline-none appearance-none"
    >
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  )
}

function ComponentRow({ comp, index, onUpdate, onDelete }) {
  const update = (field, value) => onUpdate(index, { ...comp, [field]: value })

  return (
    <div className="p-3 rounded-lg bg-zinc-800/40 border border-zinc-700/50 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-zinc-600 font-mono">#{index + 1}</span>
          {parseFloat(comp.wattage) > 1 && (
            <span className="text-[10px] text-amber-400" title="High wattage">🔥</span>
          )}
        </div>
        <button
          onClick={() => onDelete(index)}
          className="text-zinc-600 hover:text-red-400 text-xs transition-colors"
          title="Remove component"
        >✕</button>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="text-[10px] text-zinc-500">Type</label>
          <MiniSelect value={comp.type} onChange={(v) => update('type', v)} options={COMPONENT_TYPES} />
        </div>
        <div className="col-span-2">
          <label className="text-[10px] text-zinc-500">Label</label>
          <MiniInput value={comp.label} onChange={(v) => update('label', v)} placeholder="e.g. USB-C" />
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2">
        <div>
          <label className="text-[10px] text-zinc-500">X (mm)</label>
          <MiniInput value={comp.position_x} onChange={(v) => update('position_x', v)} placeholder="0" />
        </div>
        <div>
          <label className="text-[10px] text-zinc-500">Y (mm)</label>
          <MiniInput value={comp.position_y} onChange={(v) => update('position_y', v)} placeholder="0" />
        </div>
        <div>
          <label className="text-[10px] text-zinc-500">Height</label>
          <MiniInput value={comp.height} onChange={(v) => update('height', v)} placeholder="5" />
        </div>
        <div>
          <label className="text-[10px] text-zinc-500">Watts</label>
          <MiniInput value={comp.wattage} onChange={(v) => update('wattage', v)} placeholder="0" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[10px] text-zinc-500">Face Access</label>
          <MiniSelect value={comp.face_access} onChange={(v) => update('face_access', v)} options={FACE_OPTIONS} />
        </div>
        {comp.type === 'CONNECTOR' && (
          <>
            <div className="grid grid-cols-2 gap-1">
              <div>
                <label className="text-[10px] text-zinc-500">Conn W</label>
                <MiniInput value={comp.connector_width} onChange={(v) => update('connector_width', v)} placeholder="9" />
              </div>
              <div>
                <label className="text-[10px] text-zinc-500">Conn H</label>
                <MiniInput value={comp.connector_height} onChange={(v) => update('connector_height', v)} placeholder="3.5" />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function ComponentEditor({ components, onChange }) {
  const addComponent = (template = {}) => {
    const blank = {
      type: 'GENERIC', label: '', position_x: 0, position_y: 0,
      height: 5, wattage: 0, face_access: 'NONE',
      connector_width: '', connector_height: '',
      ...template,
    }
    onChange([...components, blank])
  }

  const updateComponent = (index, updated) => {
    const copy = [...components]
    copy[index] = updated
    onChange(copy)
  }

  const deleteComponent = (index) => {
    onChange(components.filter((_, i) => i !== index))
  }

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
        Components
        <span className="ml-2 text-zinc-600 font-normal normal-case">({components.length})</span>
      </h3>

      {/* Component rows */}
      <div className="space-y-2 mb-3">
        {components.map((comp, i) => (
          <ComponentRow
            key={i} comp={comp} index={i}
            onUpdate={updateComponent} onDelete={deleteComponent}
          />
        ))}
      </div>

      {/* Add buttons */}
      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => addComponent()}
          className="px-3 py-1.5 rounded text-[11px] font-medium border
            border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600
            transition-colors bg-zinc-800/50"
        >
          + Add Component
        </button>
        {Object.entries(QUICK_ADD).map(([name, template]) => (
          <button
            key={name}
            onClick={() => addComponent(template)}
            className="px-2.5 py-1.5 rounded text-[10px] border
              border-cyan-800/40 text-cyan-400/70 hover:text-cyan-300 hover:border-cyan-700
              transition-colors bg-cyan-500/5"
          >
            + {name}
          </button>
        ))}
      </div>
    </div>
  )
}
