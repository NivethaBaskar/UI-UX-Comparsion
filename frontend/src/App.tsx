import { useState, useCallback, useRef, useEffect } from 'react'
import { ConfigPanel } from './components/ConfigPanel'
import { CompareSection } from './components/CompareSection'
import { ResultsSection } from './components/ResultsSection'
import { StepsPanel } from './components/StepsPanel'
import type { LogEntry, CompareResult, JiraConfig } from './types'
import { ALL_BREAKPOINTS } from './types'

export default function App() {
  // Config
  const [apiKey, setApiKey] = useState('')
  const [jiraConfig, setJiraConfig] = useState<JiraConfig | null>(null)

  // Form
  const [figmaFile, setFigmaFile] = useState<File | null>(null)
  const [figmaPreview, setFigmaPreview] = useState<string | null>(null)
  const [url, setUrl] = useState('')
  const [selectedBreakpoints, setSelectedBreakpoints] = useState<string[]>([ALL_BREAKPOINTS[0]])
  const [mode, setMode] = useState<'classic' | 'autogen'>('classic')

  // Runtime
  const [isRunning, setIsRunning] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [results, setResults] = useState<CompareResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<string>('')
  const resultsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (results) {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [results])

  const handleFigmaFile = useCallback((file: File) => {
    setFigmaFile(file)
    const url = URL.createObjectURL(file)
    setFigmaPreview(url)
  }, [])

  const startComparison = useCallback(async () => {
    if (!figmaFile || !url.trim() || !apiKey.trim() || selectedBreakpoints.length === 0) return

    setIsRunning(true)
    setLogs([])
    setResults(null)
    setError(null)
    setActiveTab('logs')

    try {
      // Step 1: upload figma image
      const form = new FormData()
      form.append('file', figmaFile)
      const uploadRes = await fetch('/api/upload', { method: 'POST', body: form })
      if (!uploadRes.ok) throw new Error('Figma upload failed')
      const { path: figmaPath } = await uploadRes.json()

      // Step 2: stream comparison SSE
      const response = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          figma_path: figmaPath,
          url: url.trim(),
          breakpoints: selectedBreakpoints,
          mode,
          api_key: apiKey,
        }),
      })

      if (!response.body) throw new Error('No response stream')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() ?? ''

        for (const chunk of chunks) {
          if (!chunk.trim()) continue

          let eventType = 'message'
          let dataStr = ''

          for (const line of chunk.split('\n')) {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim()
            else if (line.startsWith('data: ')) dataStr = line.slice(6)
          }

          if (!dataStr) continue

          try {
            const data = JSON.parse(dataStr)
            if (eventType === 'log') {
              setLogs(prev => [...prev, data as LogEntry])
            } else if (eventType === 'result') {
              const res = data as CompareResult
              setResults(res)
              const firstBp = Object.keys(res.breakpoints)[0]
              if (firstBp) setActiveTab(firstBp)
            } else if (eventType === 'error') {
              setError(data.message)
            }
          } catch {
            // ignore parse errors on partial chunks
          }
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setError(msg)
      setLogs(prev => [...prev, { message: `Fatal error: ${msg}`, level: 'error', ts: Date.now() / 1000 }])
    } finally {
      setIsRunning(false)
    }
  }, [figmaFile, url, apiKey, selectedBreakpoints, mode])

  const hasResults = results !== null
  const showResults = hasResults || isRunning || logs.length > 0

  return (
    <div className="flex flex-col h-full min-h-screen">
      {/* Header */}
      <header className="flex items-center gap-3 px-6 py-4 border-b border-slate-200 bg-white shrink-0 shadow-sm">
        <span className="text-2xl">⚡</span>
        <div>
          <h1 className="text-lg font-bold text-slate-900 leading-tight">UI-UX Comparator</h1>
          <p className="text-xs text-slate-500">Figma design vs. live UI — AI-powered visual regression</p>
        </div>
        {isRunning && (
          <div className="ml-auto flex items-center gap-2 text-sm text-indigo-600">
            <span className="inline-block w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            Running analysis...
          </div>
        )}
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-72 shrink-0 border-r border-slate-200 overflow-y-auto bg-white">
          <ConfigPanel
            apiKey={apiKey}
            onApiKeyChange={setApiKey}
            jiraConfig={jiraConfig}
            onJiraConfigChange={setJiraConfig}
          />
        </aside>

        {/* Main */}
        <main className="flex-1 overflow-y-auto flex flex-col gap-6 p-6 bg-slate-50">
          {error && (
            <div className="card p-4 border-red-200 bg-red-50 text-red-700 text-sm flex items-start gap-2">
              <span className="text-red-500 mt-0.5">✗</span>
              <span>{error}</span>
            </div>
          )}

          <CompareSection
            figmaFile={figmaFile}
            figmaPreview={figmaPreview}
            url={url}
            selectedBreakpoints={selectedBreakpoints}
            mode={mode}
            isRunning={isRunning}
            apiKey={apiKey}
            onFigmaFile={handleFigmaFile}
            onUrlChange={setUrl}
            onBreakpointsChange={setSelectedBreakpoints}
            onModeChange={setMode}
            onCompare={startComparison}
          />

          {logs.length > 0 && (
            <StepsPanel
              logs={logs}
              breakpoints={selectedBreakpoints}
              mode={mode}
              isRunning={isRunning}
            />
          )}

          {showResults && (
            <div ref={resultsRef}>
            <ResultsSection
              results={results}
              logs={logs}
              isRunning={isRunning}
              activeTab={activeTab}
              onTabChange={setActiveTab}
              jiraConfig={jiraConfig}
              url={url}
            />
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
