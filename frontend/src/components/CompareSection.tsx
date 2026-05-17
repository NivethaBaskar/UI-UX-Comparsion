import { useRef, useState } from 'react'
import { ALL_BREAKPOINTS } from '../types'

interface Props {
  figmaFile: File | null
  figmaPreview: string | null
  url: string
  selectedBreakpoints: string[]
  mode: 'classic' | 'autogen'
  isRunning: boolean
  apiKey: string
  onFigmaFile: (f: File) => void
  onUrlChange: (v: string) => void
  onBreakpointsChange: (v: string[]) => void
  onModeChange: (v: 'classic' | 'autogen') => void
  onCompare: () => void
}

export function CompareSection({
  figmaFile,
  figmaPreview,
  url,
  selectedBreakpoints,
  mode,
  isRunning,
  apiKey,
  onFigmaFile,
  onUrlChange,
  onBreakpointsChange,
  onModeChange,
  onCompare,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [drag, setDrag] = useState(false)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDrag(false)
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) onFigmaFile(file)
  }

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onFigmaFile(file)
  }

  const toggleBp = (bp: string) => {
    if (selectedBreakpoints.includes(bp)) {
      if (selectedBreakpoints.length === 1) return
      onBreakpointsChange(selectedBreakpoints.filter(b => b !== bp))
    } else {
      onBreakpointsChange([...selectedBreakpoints, bp])
    }
  }

  const canRun =
    figmaFile !== null &&
    url.trim().length > 0 &&
    apiKey.trim().length > 0 &&
    selectedBreakpoints.length > 0 &&
    !isRunning

  return (
    <section className="card p-5 flex flex-col gap-5">
      <div className="flex items-center gap-2">
        <span className="text-base">🖼️</span>
        <h2 className="text-base font-semibold text-slate-800">New Comparison</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Figma upload */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-medium text-slate-600">
            Figma Design <span className="text-red-500">*</span>
          </label>
          <div
            onDragOver={e => { e.preventDefault(); setDrag(true) }}
            onDragLeave={() => setDrag(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`
              relative border-2 border-dashed rounded-xl cursor-pointer transition-colors duration-150
              flex items-center justify-center overflow-hidden min-h-[140px]
              ${drag
                ? 'border-indigo-400 bg-indigo-50'
                : figmaPreview
                  ? 'border-slate-300 hover:border-slate-400 bg-white'
                  : 'border-slate-300 hover:border-indigo-400 hover:bg-indigo-50/30 bg-white'
              }
            `}
          >
            <input
              ref={inputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={handleFile}
            />
            {figmaPreview ? (
              <>
                <img
                  src={figmaPreview}
                  alt="Figma design"
                  className="max-h-[200px] w-full object-contain rounded-lg"
                />
                <div className="absolute bottom-1.5 right-1.5 bg-white/90 text-xs text-slate-600 px-2 py-0.5 rounded shadow-sm border border-slate-200">
                  {figmaFile?.name}
                </div>
                <div className="absolute top-1.5 right-1.5 bg-white/90 text-xs text-slate-500 px-2 py-0.5 rounded shadow-sm border border-slate-200 hover:text-slate-700">
                  click to change
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center gap-2 text-slate-400 p-6">
                <span className="text-3xl">📁</span>
                <p className="text-sm font-medium text-slate-500">Drop PNG / JPG here</p>
                <p className="text-xs text-slate-400">or click to browse</p>
              </div>
            )}
          </div>
        </div>

        {/* URL + options */}
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-600">
              Live URL <span className="text-red-500">*</span>
            </label>
            <input
              type="url"
              value={url}
              onChange={e => onUrlChange(e.target.value)}
              placeholder="https://example.com"
              className="input-field"
            />
          </div>

          {/* Breakpoints */}
          <div className="flex flex-col gap-2">
            <label className="text-xs font-medium text-slate-600">Breakpoints</label>
            <div className="flex flex-col gap-1.5">
              {ALL_BREAKPOINTS.map(bp => (
                <label key={bp} className="flex items-center gap-2.5 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={selectedBreakpoints.includes(bp)}
                    onChange={() => toggleBp(bp)}
                    className="w-4 h-4 rounded border-slate-300 bg-white text-indigo-600 focus:ring-indigo-500 focus:ring-offset-white"
                  />
                  <span className="text-sm text-slate-600 group-hover:text-slate-900 transition-colors">
                    {bp}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Mode */}
          <div className="flex flex-col gap-2">
            <label className="text-xs font-medium text-slate-600">Analysis Mode</label>
            <div className="flex rounded-lg border border-slate-300 overflow-hidden text-sm bg-white shadow-sm">
              <button
                onClick={() => onModeChange('classic')}
                className={`flex-1 py-2 font-medium transition-colors ${
                  mode === 'classic'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'
                }`}
              >
                Classic
              </button>
              <button
                onClick={() => onModeChange('autogen')}
                className={`flex-1 py-2 font-medium transition-colors ${
                  mode === 'autogen'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'
                }`}
              >
                AutoGen (3-agent)
              </button>
            </div>
            <p className="text-xs text-slate-400">
              {mode === 'autogen'
                ? 'AnalysisAgent → CritiqueAgent → SeverityAgent pipeline'
                : 'Single GPT-4o vision call with enrichment step'}
            </p>
          </div>
        </div>
      </div>

      {/* Action */}
      <div className="flex items-center gap-4 pt-1 border-t border-slate-200">
        <button
          onClick={onCompare}
          disabled={!canRun}
          className="btn-primary flex items-center gap-2"
        >
          {isRunning ? (
            <>
              <span className="inline-block w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              Comparing...
            </>
          ) : (
            <>
              <span>▶</span>
              Compare UI
            </>
          )}
        </button>

        {!apiKey && (
          <span className="text-xs text-amber-600">Set your OpenAI API key in the sidebar</span>
        )}
        {apiKey && !figmaFile && (
          <span className="text-xs text-slate-400">Upload a Figma design to start</span>
        )}
        {apiKey && figmaFile && !url.trim() && (
          <span className="text-xs text-slate-400">Enter a live URL to compare against</span>
        )}
      </div>
    </section>
  )
}
