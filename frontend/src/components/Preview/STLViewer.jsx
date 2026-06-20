/**
 * EnclosureAI — Three.js STL Viewer
 * WebGL 3D preview with OrbitControls, wireframe toggle, body/lid switch.
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { STLLoader } from 'three/addons/loaders/STLLoader.js'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const BG_COLOR = 0x1a1a2e
const CYAN = 0x0891b2
const GRID_COLOR = 0x2a2a3e

export default function STLViewer({ jobId, strategy }) {
  const containerRef = useRef(null)
  const rendererRef = useRef(null)
  const sceneRef = useRef(null)
  const cameraRef = useRef(null)
  const controlsRef = useRef(null)
  const meshRef = useRef(null)
  const frameRef = useRef(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [wireframe, setWireframe] = useState(false)
  const [part, setPart] = useState('body')

  // ── Initialize Three.js scene ──
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(BG_COLOR)
    sceneRef.current = scene

    // Camera
    const aspect = container.clientWidth / container.clientHeight
    const camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 2000)
    camera.position.set(80, 60, 80)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.minDistance = 10
    controls.maxDistance = 500
    controlsRef.current = controls

    // Lights
    const ambient = new THREE.AmbientLight(0xffffff, 0.4)
    scene.add(ambient)

    const dir1 = new THREE.DirectionalLight(0xffffff, 0.8)
    dir1.position.set(50, 80, 50)
    dir1.castShadow = true
    scene.add(dir1)

    const dir2 = new THREE.DirectionalLight(0x8888ff, 0.3)
    dir2.position.set(-40, 20, -40)
    scene.add(dir2)

    // Grid
    const grid = new THREE.GridHelper(200, 20, GRID_COLOR, GRID_COLOR)
    grid.material.opacity = 0.3
    grid.material.transparent = true
    scene.add(grid)

    // Animate
    const animate = () => {
      frameRef.current = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // Resize observer
    const ro = new ResizeObserver(([entry]) => {
      const w = entry.contentRect.width
      const h = entry.contentRect.height
      if (w && h) {
        camera.aspect = w / h
        camera.updateProjectionMatrix()
        renderer.setSize(w, h)
      }
    })
    ro.observe(container)

    return () => {
      cancelAnimationFrame(frameRef.current)
      ro.disconnect()
      controls.dispose()
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  // ── Load STL when jobId or part changes ──
  const loadSTL = useCallback((url) => {
    const scene = sceneRef.current
    const camera = cameraRef.current
    const controls = controlsRef.current
    if (!scene || !camera) return

    // Remove existing mesh
    if (meshRef.current) {
      scene.remove(meshRef.current)
      meshRef.current.geometry.dispose()
      meshRef.current.material.dispose()
      meshRef.current = null
    }

    setLoading(true)
    setError(null)

    const loader = new STLLoader()
    loader.load(
      url,
      (geometry) => {
        geometry.computeVertexNormals()
        geometry.center()

        const material = new THREE.MeshPhongMaterial({
          color: CYAN,
          specular: 0x444444,
          shininess: 30,
          wireframe: wireframe,
          flatShading: false,
        })

        const mesh = new THREE.Mesh(geometry, material)
        mesh.castShadow = true
        mesh.receiveShadow = true
        scene.add(mesh)
        meshRef.current = mesh

        // Auto-fit camera
        const box = new THREE.Box3().setFromObject(mesh)
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)
        const dist = maxDim * 2.5

        camera.position.set(dist * 0.7, dist * 0.5, dist * 0.7)
        controls.target.set(0, 0, 0)
        controls.update()

        setLoading(false)
      },
      undefined,
      (err) => {
        console.error('STL load error:', err)
        setError('Failed to load STL preview')
        setLoading(false)
      }
    )
  }, [wireframe])

  useEffect(() => {
    if (!jobId) return
    const url =
  `http://127.0.0.1:8000/generated_files/${jobId}/body.stl`
    loadSTL(url)
  }, [jobId, part, loadSTL])

  // ── Wireframe toggle ──
  useEffect(() => {
    if (meshRef.current) {
      meshRef.current.material.wireframe = wireframe
    }
  }, [wireframe])

  const resetCamera = () => {
    const camera = cameraRef.current
    const controls = controlsRef.current
    if (camera && controls) {
      camera.position.set(80, 60, 80)
      controls.target.set(0, 0, 0)
      controls.update()
    }
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 overflow-hidden">
      {/* Viewer canvas */}
      <div
        ref={containerRef}
        className="w-full aspect-[4/3] relative"
      >
        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-zinc-900/80 z-10">
            <div className="text-center">
              <svg className="w-8 h-8 animate-spin text-cyan-400 mx-auto mb-2" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                <path className="opacity-75" fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <p className="text-xs text-zinc-400">Loading 3D preview...</p>
            </div>
          </div>
        )}

        {/* Error overlay */}
        {error && !loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-zinc-900/80 z-10">
            <div className="text-center px-6">
              <p className="text-sm text-zinc-400">Preview unavailable</p>
              <p className="text-xs text-zinc-600 mt-1">STL can still be downloaded</p>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!jobId && !loading && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-center">
              <div className="text-4xl mb-3 opacity-30">📐</div>
              <p className="text-zinc-500 text-sm">3D Preview</p>
              <p className="text-zinc-700 text-xs mt-1">Generate an enclosure to preview</p>
            </div>
          </div>
        )}

        {/* Strategy badge */}
        {strategy && jobId && !loading && (
          <div className="absolute top-3 left-3 z-20">
            <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-[10px]
              font-bold tracking-wide border backdrop-blur-sm shadow-lg
              ${strategy === 'CLAMSHELL_HORIZONTAL' || strategy === 'CLAMSHELL_VERTICAL'
                ? 'text-green-300 bg-green-500/20 border-green-500/40'
                : strategy === 'CHIMNEY_THERMAL'
                ? 'text-amber-300 bg-amber-500/20 border-amber-500/40'
                : strategy === 'DIN_RAIL_CLIP'
                ? 'text-blue-300 bg-blue-500/20 border-blue-500/40'
                : strategy === 'WEARABLE_ROUNDED'
                ? 'text-purple-300 bg-purple-500/20 border-purple-500/40'
                : strategy === 'SEALED_IP_RATED'
                ? 'text-red-300 bg-red-500/20 border-red-500/40'
                : 'text-cyan-300 bg-cyan-500/20 border-cyan-500/40'
              }`}>
              Strategy: {strategy}
            </span>
          </div>
        )}
      </div>

      {/* Controls bar */}
      <div className="flex items-center justify-between px-4 py-2 border-t border-zinc-800 bg-zinc-900">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPart('body')}
            className={`px-3 py-1 rounded text-[11px] font-medium transition-colors
              ${part === 'body'
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                : 'text-zinc-500 hover:text-zinc-300'}`}
          >Body</button>
          <button
            onClick={() => setPart('lid')}
            className={`px-3 py-1 rounded text-[11px] font-medium transition-colors
              ${part === 'lid'
                ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30'
                : 'text-zinc-500 hover:text-zinc-300'}`}
          >Lid</button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setWireframe(!wireframe)}
            className={`px-2.5 py-1 rounded text-[10px] transition-colors
              ${wireframe
                ? 'bg-zinc-700 text-zinc-200'
                : 'text-zinc-500 hover:text-zinc-300'}`}
            title="Toggle wireframe"
          >◇ Wire</button>
          <button
            onClick={resetCamera}
            className="px-2.5 py-1 rounded text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
            title="Reset camera"
          >↺ Reset</button>
        </div>
      </div>
    </div>
  )
}
