/**
 * EnclosureAI — Preset Selector
 * Three preset cards + Custom option. One-click auto-fill.
 */

const PRESETS = {
  ESP32: {
    name: 'ESP32 DevKit V1',
    dims: '51 × 25 mm',
    icon: '⚡',
    pcb: { length: 51, width: 25, thickness: 1.6, mounting_hole_diameter: 3.2 },
    components: [
      { type: 'CONNECTOR', label: 'USB-C', position_x: 25.5, position_y: 0, height: 3.5,
        wattage: 0, face_access: 'FRONT', connector_width: 9, connector_height: 3.5 },
      { type: 'HEATSINK', label: 'Voltage Regulator', position_x: 10, position_y: 12.5,
        height: 3, wattage: 1.5, face_access: 'NONE' },
    ],
    material: 'PETG',
  },
  ARDUINO_UNO: {
    name: 'Arduino Uno R3',
    dims: '68.6 × 53.4 mm',
    icon: '🔧',
    pcb: { length: 68.6, width: 53.4, thickness: 1.6, mounting_hole_diameter: 3.2 },
    components: [
      { type: 'CONNECTOR', label: 'USB-B', position_x: 34.3, position_y: 53.4, height: 11,
        wattage: 0, face_access: 'BACK', connector_width: 12, connector_height: 11 },
      { type: 'CONNECTOR', label: 'Barrel Jack', position_x: 0, position_y: 26.7, height: 11,
        wattage: 0, face_access: 'LEFT', connector_width: 9, connector_height: 11 },
      { type: 'HEATSINK', label: 'Voltage Regulator', position_x: 5, position_y: 22,
        height: 4, wattage: 2.0, face_access: 'NONE' },
    ],
    material: 'PLA',
  },
  RPI4: {
    name: 'Raspberry Pi 4',
    dims: '85 × 56 mm',
    icon: '🍓',
    pcb: { length: 85, width: 56, thickness: 1.6, mounting_hole_diameter: 2.7 },
    components: [
      { type: 'CONNECTOR', label: 'USB-C Power', position_x: 11.2, position_y: 0, height: 3.5,
        wattage: 0, face_access: 'FRONT', connector_width: 9, connector_height: 3.5 },
      { type: 'CONNECTOR', label: 'HDMI 0', position_x: 25.5, position_y: 0, height: 6.5,
        wattage: 0, face_access: 'FRONT', connector_width: 7, connector_height: 3.5 },
      { type: 'CONNECTOR', label: 'Ethernet', position_x: 85, position_y: 28, height: 14,
        wattage: 0, face_access: 'RIGHT', connector_width: 16, connector_height: 14 },
      { type: 'HEATSINK', label: 'SoC', position_x: 42.5, position_y: 28, height: 5,
        wattage: 5.0, face_access: 'NONE' },
    ],
    material: 'PETG',
  },
}

export default function PresetSelector({ onSelect, activePreset }) {
  const presetKeys = ['ESP32', 'ARDUINO_UNO', 'RPI4']

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
        Board Preset
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {presetKeys.map(key => {
          const p = PRESETS[key]
          const isActive = activePreset === key
          return (
            <button
              key={key}
              onClick={() => onSelect(key, PRESETS[key])}
              className={`p-3 rounded-lg border text-left transition-all duration-150
                ${isActive
                  ? 'border-cyan-500 bg-cyan-500/10 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
                  : 'border-zinc-700 bg-zinc-800/50 hover:border-zinc-600 hover:bg-zinc-800'
                }`}
            >
              <div className="text-lg mb-1">{p.icon}</div>
              <div className="text-xs font-medium text-zinc-200 leading-tight">{p.name}</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">{p.dims}</div>
            </button>
          )
        })}
        <button
          onClick={() => onSelect(null, null)}
          className={`p-3 rounded-lg border text-left transition-all duration-150
            ${activePreset === null && activePreset !== undefined
              ? 'border-cyan-500 bg-cyan-500/10'
              : 'border-zinc-700 bg-zinc-800/50 hover:border-zinc-600 hover:bg-zinc-800'
            }`}
        >
          <div className="text-lg mb-1">✏️</div>
          <div className="text-xs font-medium text-zinc-200">Custom</div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Enter manually</div>
        </button>
      </div>
    </div>
  )
}

export { PRESETS }
