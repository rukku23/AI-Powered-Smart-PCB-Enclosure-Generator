/**
 * EnclosureAI — Download Panel
 * ZIP download, individual file links, and BOM preview.
 */
import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const FILES = [
  { key: 'body_stl', name: 'enclosure_body.stl', icon: '📦', desc: '3D print file — main body' },
  { key: 'lid_stl', name: 'enclosure_lid.stl', icon: '📦', desc: '3D print file — lid' },
  { key: 'scad', name: 'enclosure_full.scad', icon: '📝', desc: 'Editable OpenSCAD source' },
  { key: 'step', name: 'enclosure_assembly.step', icon: '🔷', desc: 'Import to Fusion 360 / SolidWorks' },
  { key: 'thermal', name: 'thermal_report.json', icon: '📊', desc: 'Thermal analysis data' },
  { key: 'bom', name: 'bom.csv', icon: '📋', desc: 'Bill of materials + print settings' },
  { key: 'reasoning', name: 'ai_reasoning.txt', icon: '🤖', desc: 'AI design decision log' },
]

export default function DownloadPanel({ jobId }) {
  const [bomData, setBomData] = useState(null)

  useEffect(() => {
    if (!jobId) return
    fetch(`${API_URL}/api/bom/${jobId}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => setBomData(data))
      .catch(() => setBomData(null))
  }, [jobId])

  if (!jobId) return null

  const downloadUrl = `${API_URL}/api/download/${jobId}`

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
        Downloads
      </h3>

      {/* Primary ZIP download */}
      <a
        href={downloadUrl}
        download
        className="block w-full py-3 px-4 rounded-lg font-semibold text-sm text-center
          bg-gradient-to-r from-cyan-500 to-cyan-600
          hover:from-cyan-400 hover:to-cyan-500
          text-zinc-950 transition-all duration-200
          shadow-[0_0_20px_rgba(6,182,212,0.15)]
          hover:shadow-[0_0_30px_rgba(6,182,212,0.25)]"
      >
        ⬇ Download All (ZIP)
      </a>

      {/* Individual files */}
      <div className="space-y-1">
        {FILES.map(f => (
          <div key={f.key}
            className="flex items-center gap-3 py-2 px-3 rounded-lg
              hover:bg-zinc-800/50 transition-colors group"
          >
            <span className="text-sm flex-shrink-0">{f.icon}</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-zinc-300 font-medium truncate">{f.name}</p>
              <p className="text-[10px] text-zinc-600 truncate">{f.desc}</p>
            </div>
            <a
              href={`${downloadUrl}?file=${f.key}`}
              className="text-[10px] text-cyan-500 hover:text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
            >
              Download
            </a>
          </div>
        ))}
      </div>

      {/* BOM Preview */}
      {bomData && bomData.filament && (
        <div className="pt-3 border-t border-zinc-800">
          <h4 className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600 mb-2">
            Print Estimate
          </h4>
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center">
              <p className="text-lg font-bold text-zinc-200">
                {bomData.filament.weight_g}g
              </p>
              <p className="text-[10px] text-zinc-600">{bomData.filament.material}</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-zinc-200">
                {bomData.filament.length_m}m
              </p>
              <p className="text-[10px] text-zinc-600">Filament</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-zinc-200">
                {bomData.print_settings?.estimated_print_hours || '—'}h
              </p>
              <p className="text-[10px] text-zinc-600">Print Time</p>
            </div>
          </div>
          {bomData.fasteners && bomData.fasteners.length > 0 && (
            <div className="mt-2 space-y-1">
              {bomData.fasteners.map((f, i) => (
                <p key={i} className="text-[10px] text-zinc-500">
                  • {f.quantity}× {f.description}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
