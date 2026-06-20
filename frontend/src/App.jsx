/**
 * EnclosureAI — Main Application
 * 
 * Two-column layout:
 *   Left (40%):  Input form — presets, PCB dims, components, feature toggles
 *   Right (60%): Preview — STL viewer, thermal card, downloads, reasoning
 * 
 * Top navbar with logo and API health status indicator.
 */

import { useState, useEffect } from 'react'
import { checkHealth } from './api/client'

// Input Form Components
import PresetSelector from './components/shared/PresetSelector'
import PCBDimensionsPanel from './components/InputForm/PCBDimensionsPanel'
import ComponentEditor from './components/InputForm/ComponentEditor'
import FeatureToggles from './components/InputForm/FeatureToggles'

// Preview Components
import STLViewer from './components/Preview/STLViewer'
import ThermalScoreCard from './components/Preview/ThermalScoreCard'

// Output Components
import DownloadPanel from './components/Output/DownloadPanel'
import ReasoningBlock from './components/Output/ReasoningBlock'

// Shared Components
import ProgressStream from './components/shared/ProgressStream'

// Hooks
import useGeneration from './hooks/useGeneration'

export default function App() {
  // ─── API Health State ────────────────────────────────────────
  const [apiStatus, setApiStatus] = useState('checking') // 'checking' | 'online' | 'offline'

  useEffect(() => {
    const checkApi = async () => {
      try {
        await checkHealth()
        setApiStatus('online')
      } catch {
        setApiStatus('offline')
      }
    }
    checkApi()
    const interval = setInterval(checkApi, 30000)
    return () => clearInterval(interval)
  }, [])

  // ─── Form State ──────────────────────────────────────────────
  const [preset, setPreset] = useState(null)
  const [formData, setFormData] = useState({
    pcb: { length: '', width: '', thickness: 1.6, mounting_hole_diameter: 3.2 },
    components: [],
    material: 'PETG',
    print_technology: 'FDM',
    lid_style: 'SNAP_FIT',
    ventilation: true,
    display_window: false,
    aesthetic_style: 'MINIMAL',
    design_context: {
      use_case: 'BENCH_PROTOTYPE',
      access_frequency: 'RARELY',
      mounting: 'DESKTOP',
      environment: 'INDOOR',
    },
  })

  // ─── Generation State ────────────────────────────────────────
  const { state: genState, generate, reset } = useGeneration()

  // ─── Handlers ────────────────────────────────────────────────
  const handlePresetSelect = (presetId, presetData) => {
    setPreset(presetId)
    if (presetData) {
      setFormData(prev => ({
        ...prev,
        pcb: { ...presetData.pcb },
        components: presetData.components ? [...presetData.components] : [],
        material: presetData.material || prev.material,
      }))
    } else {
      // Custom — clear fields
      setFormData(prev => ({
        ...prev,
        pcb: { length: '', width: '', thickness: 1.6, mounting_hole_diameter: 3.2 },
        components: [],
      }))
    }
  }

  const handleGenerate = () => {
    // Validate required fields
    const pcb = formData.pcb
    if (!pcb.length || !pcb.width) return
    const l = parseFloat(pcb.length)
    const w = parseFloat(pcb.width)
    if (l < 10 || l > 500 || w < 10 || w > 500) return

    generate({ ...formData, preset })
  }

  const isGenerating = !['idle', 'complete', 'error'].includes(genState.status)

  // ─── Render ──────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">

      {/* ═══ Navbar ═══════════════════════════════════════════════ */}
      <nav className="sticky top-0 z-50 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
        <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center">
              <span className="text-sm font-bold text-zinc-950">E</span>
            </div>
            <span className="text-lg font-semibold tracking-tight">
              Enclosure<span className="text-cyan-400">AI</span>
            </span>
          </div>

          {/* Status Indicator */}
          <div className="flex items-center gap-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${
              apiStatus === 'online' ? 'bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.5)]' :
              apiStatus === 'offline' ? 'bg-red-400' :
              'bg-zinc-500 animate-pulse'
            }`} />
            <span className="text-zinc-500">
              {apiStatus === 'online' ? 'API Connected' :
               apiStatus === 'offline' ? 'API Offline' :
               'Checking...'}
            </span>
          </div>
        </div>
      </nav>

      {/* ═══ Main Content ═════════════════════════════════════════ */}
      <main className="max-w-screen-2xl mx-auto px-4 sm:px-6 py-6">
        <div className="flex flex-col lg:flex-row gap-6">

          {/* ─── Left Column: Input Form (40%) ─────────────────── */}
          <aside className="w-full lg:w-[40%] lg:sticky lg:top-20 lg:self-start space-y-5">
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 space-y-6">

              {/* Preset Selector */}
              <PresetSelector onSelect={handlePresetSelect} activePreset={preset} />

              <hr className="border-zinc-800" />

              {/* PCB Dimensions */}
              <PCBDimensionsPanel formData={formData} onChange={setFormData} />

              <hr className="border-zinc-800" />

              {/* Component Editor */}
              <ComponentEditor
                components={formData.components}
                onChange={(components) => setFormData(prev => ({ ...prev, components }))}
              />

              <hr className="border-zinc-800" />

              {/* Feature Toggles */}
              <FeatureToggles formData={formData} onChange={setFormData} />
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={isGenerating || !formData.pcb.length || !formData.pcb.width}
              className="w-full py-3 px-4 rounded-lg font-semibold text-sm
                bg-gradient-to-r from-cyan-500 to-cyan-600
                hover:from-cyan-400 hover:to-cyan-500
                disabled:from-zinc-700 disabled:to-zinc-700 disabled:text-zinc-500
                text-zinc-950 transition-all duration-200
                shadow-[0_0_20px_rgba(6,182,212,0.15)]
                hover:shadow-[0_0_30px_rgba(6,182,212,0.25)]
                disabled:shadow-none"
            >
              {isGenerating ? '⏳ Generating...' : '⚡ Generate Enclosure'}
            </button>

            {/* Progress Stream */}
            <ProgressStream
              status={genState.status}
              reasoning={genState.reasoning}
              attempt={genState.attempt}
              error={genState.error}
            />
          </aside>

          {/* ─── Right Column: Preview (60%) ───────────────────── */}
          <section className="w-full lg:w-[60%] space-y-5">

            {/* 3D STL Viewer */}
            <STLViewer jobId={genState.jobId} strategy={genState.strategy} />

            {/* Thermal Score Card */}
            <ThermalScoreCard thermalReport={genState.thermalReport} />

            {/* Download Panel */}
            <DownloadPanel jobId={genState.jobId} />

            {/* Reasoning Block (full version after generation) */}
            <ReasoningBlock reasoning={genState.reasoning} />
          </section>

        </div>
      </main>

      {/* ═══ Footer ═══════════════════════════════════════════════ */}
      <footer className="border-t border-zinc-800 mt-12 py-6">
        <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 text-center text-xs text-zinc-600">
          EnclosureAI — AI-Powered PCB Enclosure Generation · AntiGravity 2025
        </div>
      </footer>
    </div>
  )
}
