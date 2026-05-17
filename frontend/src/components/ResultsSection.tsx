import { useState, useRef } from 'react'
import type { CompareResult, JiraConfig, BreakpointResult, A11yIssue } from '../types'
import { BP_SUFFIX } from '../types'
import { IssueTable } from './IssueTable'
import { LogsPanel } from './LogsPanel'
import type { LogEntry } from '../types'

interface Props {
  results: CompareResult | null
  logs: LogEntry[]
  isRunning: boolean
  activeTab: string
  onTabChange: (tab: string) => void
  jiraConfig: JiraConfig | null
  url: string
  elapsedSeconds: number | null
}

export function ResultsSection({
  results,
  logs,
  isRunning,
  activeTab,
  onTabChange,
  jiraConfig,
  url,
  elapsedSeconds,
}: Props) {
  const bpKeys = results ? Object.keys(results.breakpoints) : []
  const tabs = [...bpKeys, 'logs']

  const activeResult = results?.breakpoints[activeTab] ?? null

  return (
    <section className="card flex flex-col overflow-hidden">
      {/* ROI banner */}
      {results && elapsedSeconds !== null && (
        <ROIBanner results={results} elapsedSeconds={elapsedSeconds} />
      )}

      {/* Tabs bar */}
      <div className="flex items-center border-b border-slate-200 px-4 pt-3 gap-1 overflow-x-auto bg-white">
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className={`tab-btn shrink-0 ${
              activeTab === tab ? 'tab-btn-active' : 'tab-btn-inactive'
            }`}
          >
            {tab === 'logs' ? (
              <span className="flex items-center gap-1.5">
                <span>📋</span>
                Logs
                {(isRunning || logs.length > 0) && (
                  <span
                    className={`text-xs px-1.5 rounded-full ${
                      isRunning
                        ? 'bg-indigo-600 text-white animate-pulse'
                        : 'bg-slate-200 text-slate-500'
                    }`}
                  >
                    {logs.length}
                  </span>
                )}
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <BpIcon bp={tab} />
                {tab}
                {results?.breakpoints[tab] && (
                  <MismatchBadge pct={results.breakpoints[tab].mismatch_pct} />
                )}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'logs' ? (
          <div className="h-[500px]">
            <LogsPanel logs={logs} isRunning={isRunning} />
          </div>
        ) : activeResult ? (
          <BreakpointView
            bpLabel={activeTab}
            result={activeResult}
            jiraConfig={jiraConfig}
            url={url}
          />
        ) : (
          <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
            {isRunning ? 'Waiting for results...' : 'No data'}
          </div>
        )}
      </div>
    </section>
  )
}

const HOURLY_RATE = 60      // $/hr for a QA engineer
const MINS_PER_ISSUE = 30  // avg manual QA time per issue

function ROIBanner({ results, elapsedSeconds }: { results: CompareResult; elapsedSeconds: number }) {
  const bpKeys = Object.keys(results.breakpoints)
  const totalIssues = bpKeys.reduce(
    (sum, bp) => sum + results.breakpoints[bp].issues.filter(i => i.type !== 'error').length,
    0,
  )
  const manualMins = totalIssues * MINS_PER_ISSUE
  const savings = Math.round((manualMins / 60) * HOURLY_RATE)

  const fmt = (s: number) => s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3 bg-emerald-50 border-b border-emerald-200 text-sm">
      <span className="text-emerald-700 font-semibold">
        This analysis found{' '}
        <span className="text-emerald-900 font-bold">{totalIssues} issues</span>{' '}
        across{' '}
        <span className="text-emerald-900 font-bold">{bpKeys.length} breakpoint{bpKeys.length !== 1 ? 's' : ''}</span>.
      </span>
      <span className="flex items-center gap-4 text-emerald-600">
        <span>Manual QA equivalent: <strong>~{manualMins} min</strong></span>
        <span className="text-emerald-300">|</span>
        <span>Tool took: <strong>{fmt(elapsedSeconds)}</strong></span>
        <span className="text-emerald-300">|</span>
        <span className="text-emerald-800 font-bold">
          Estimated savings: ${savings}
          <span className="font-normal text-emerald-600"> at ${HOURLY_RATE}/hr</span>
        </span>
      </span>
    </div>
  )
}

function BpIcon({ bp }: { bp: string }) {
  if (bp.includes('Mobile')) return <span>📱</span>
  if (bp.includes('Tablet')) return <span>💻</span>
  return <span>🖥️</span>
}

function MismatchBadge({ pct }: { pct: number }) {
  const color = pct > 15 ? 'text-red-500' : pct > 5 ? 'text-amber-600' : 'text-emerald-600'
  return <span className={`text-xs font-medium ${color}`}>{pct.toFixed(1)}%</span>
}

// ── Per-breakpoint view ───────────────────────────────────────────────────────

interface BpViewProps {
  bpLabel: string
  result: BreakpointResult
  jiraConfig: JiraConfig | null
  url: string
}

function BreakpointView({ bpLabel, result, jiraConfig, url }: BpViewProps) {
  const [lightbox, setLightbox] = useState<string | null>(null)
  const [creatingTickets, setCreatingTickets] = useState(false)
  const [ticketResults, setTicketResults] = useState<any[] | null>(null)
  const [severityThreshold, setSeverityThreshold] = useState('medium')
  const [viewMode, setViewMode] = useState<'slider' | 'sidebyside'>('sidebyside')

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(result.issues, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `ui-issues-${BP_SUFFIX[bpLabel] ?? 'unknown'}.json`
    a.click()
  }

  const createTickets = async () => {
    if (!jiraConfig) return
    setCreatingTickets(true)
    setTicketResults(null)
    try {
      const res = await fetch('/api/create-tickets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jira_domain:        jiraConfig.domain,
          jira_email:         jiraConfig.email,
          jira_token:         jiraConfig.token,
          jira_project:       jiraConfig.project,
          issues:             result.issues,
          url,
          suffix:             BP_SUFFIX[bpLabel] ?? '1440',
          severity_threshold: severityThreshold,
        }),
      })
      const data = await res.json()
      setTicketResults(data.results ?? [])
    } catch (e) {
      setTicketResults([{ status: 'failed', message: String(e) }])
    } finally {
      setCreatingTickets(false)
    }
  }

  return (
    <div className="p-5 flex flex-col gap-6 overflow-y-auto max-h-[80vh]">
      {/* Mismatch headline */}
      <div className="flex items-center gap-4">
        <div
          className={`text-3xl font-bold ${
            result.mismatch_pct > 15
              ? 'text-red-500'
              : result.mismatch_pct > 5
              ? 'text-amber-500'
              : 'text-emerald-600'
          }`}
        >
          {result.mismatch_pct.toFixed(2)}%
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-800">Pixel Mismatch</p>
          <p className="text-xs text-slate-400">{bpLabel}</p>
        </div>
      </div>

      {/* Image comparison — view mode toggle */}
      <div className="flex flex-col gap-3">
        {/* Toggle tabs */}
        <div className="flex items-center gap-1 self-start bg-slate-100 rounded-lg p-1">
          <button
            onClick={() => setViewMode('slider')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              viewMode === 'slider'
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            ⇔ Slider
          </button>
          <button
            onClick={() => setViewMode('sidebyside')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              viewMode === 'sidebyside'
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            ▦ Side by Side
          </button>
        </div>

        {/* Slider view */}
        {viewMode === 'slider' && (
          <div className="flex flex-col gap-4">
            <ComparisonSlider
              img1={result.figma_image}
              img2={result.annotated_image || result.ui_image}
              label1="Figma Design"
              label2="Live UI — Annotated"
              onClickImg1={() => setLightbox(result.figma_image)}
              onClickImg2={() => setLightbox(result.annotated_image || result.ui_image)}
            />
            <ImageCard
              label={`Pixel Diff (${result.mismatch_pct.toFixed(2)}% mismatch)`}
              src={result.diff_image}
              accent="border-amber-200"
              headerColor="bg-amber-50"
              onClick={() => setLightbox(result.diff_image)}
            />
          </div>
        )}

        {/* Side-by-side view */}
        {viewMode === 'sidebyside' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <ImageCard
              label="Figma Design"
              src={result.figma_image}
              accent="border-indigo-200"
              headerColor="bg-indigo-50"
              onClick={() => setLightbox(result.figma_image)}
            />
            <ImageCard
              label="Live UI — Annotated"
              src={result.annotated_image || result.ui_image}
              accent="border-red-200"
              headerColor="bg-red-50"
              badge="Issues highlighted"
              onClick={() => setLightbox(result.annotated_image || result.ui_image)}
            />
            <ImageCard
              label={`Pixel Diff (${result.mismatch_pct.toFixed(2)}% mismatch)`}
              src={result.diff_image}
              accent="border-amber-200"
              headerColor="bg-amber-50"
              onClick={() => setLightbox(result.diff_image)}
            />
          </div>
        )}
      </div>

      {/* Issues table */}
      <IssueTable
        issues={result.issues}
        onDownload={downloadJson}
        filename={`ui-issues-${BP_SUFFIX[bpLabel] ?? 'unknown'}`}
      />

      {/* Accessibility section */}
      {result.a11y_issues?.length > 0 && (
        <AccessibilityPanel issues={result.a11y_issues} />
      )}

      {/* Jira section */}
      {jiraConfig && result.issues.length > 0 && (
        <div className="border border-slate-200 rounded-xl p-4 flex flex-col gap-3 bg-slate-50">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-800 flex items-center gap-2">
              <span>🎫</span> Create Jira Tickets
            </span>
            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-500">Min severity:</label>
              <select
                value={severityThreshold}
                onChange={e => setSeverityThreshold(e.target.value)}
                className="bg-white border border-slate-300 rounded px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-indigo-500 shadow-sm"
              >
                <option value="critical">Critical only</option>
                <option value="high">High+</option>
                <option value="medium">Medium+</option>
                <option value="low">All</option>
              </select>
              <button
                onClick={createTickets}
                disabled={creatingTickets}
                className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5"
              >
                {creatingTickets ? (
                  <>
                    <span className="inline-block w-3 h-3 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Tickets'
                )}
              </button>
            </div>
          </div>

          {ticketResults && (
            <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto">
              {ticketResults.map((r: any, i: number) => (
                <div
                  key={i}
                  className={`flex flex-col gap-0.5 text-xs px-3 py-1.5 rounded-lg ${
                    r.status === 'created'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : r.status === 'skipped'
                      ? 'bg-slate-100 text-slate-500 border border-slate-200'
                      : 'bg-red-50 text-red-700 border border-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2">
                  <span>
                    {r.status === 'created' ? '✓' : r.status === 'skipped' ? '–' : '✗'}
                  </span>
                  <span className="font-medium">
                    {r.status === 'created'
                      ? r.ticket_key
                      : r.status === 'skipped'
                      ? `Skipped — ${r.issue?.component ?? ''} (${r.reason ?? 'below threshold'})`
                      : `Failed — ${r.issue?.component ?? ''}`}
                  </span>
                  {r.ticket_url && (
                    <a
                      href={r.ticket_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-auto underline opacity-75 hover:opacity-100"
                    >
                      open ↗
                    </a>
                  )}
                  </div>
                  {r.status === 'failed' && r.error && (
                    <span className="text-red-500 pl-5 break-all">{r.error}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Lightbox */}
      {lightbox && (
        <div
          className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6 backdrop-blur-sm"
          onClick={() => setLightbox(null)}
        >
          <img
            src={lightbox}
            alt="full size"
            className="max-h-full max-w-full object-contain rounded-xl shadow-2xl"
          />
          <button
            onClick={() => setLightbox(null)}
            className="absolute top-4 right-4 text-slate-700 bg-white hover:bg-slate-100 rounded-full w-8 h-8 flex items-center justify-center text-lg shadow-md"
          >
            ×
          </button>
        </div>
      )}
    </div>
  )
}

function AccessibilityPanel({ issues }: { issues: A11yIssue[] }) {
  const [open, setOpen] = useState(true)
  const high = issues.filter(i => i.severity === 'high').length
  const med  = issues.filter(i => i.severity === 'medium').length

  return (
    <div className="border border-amber-200 rounded-xl overflow-hidden bg-amber-50">
      {/* Header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-amber-100 transition-colors"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-amber-800">
          ♿ Accessibility — WCAG 2.1 AA Contrast Check
          <span className="flex items-center gap-1.5 ml-2">
            {high > 0 && (
              <span className="bg-red-100 text-red-700 border border-red-200 text-xs font-medium px-2 py-0.5 rounded-full">
                {high} high
              </span>
            )}
            {med > 0 && (
              <span className="bg-amber-100 text-amber-700 border border-amber-300 text-xs font-medium px-2 py-0.5 rounded-full">
                {med} medium
              </span>
            )}
          </span>
        </span>
        <span className="text-amber-500 text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {/* Body */}
      {open && (
        <div className="border-t border-amber-200 divide-y divide-amber-100">
          {issues.map((issue, i) => (
            <div key={i} className="flex items-start gap-3 px-4 py-3">
              {/* Contrast badge */}
              <div className={`shrink-0 flex flex-col items-center justify-center w-14 h-14 rounded-lg border text-center ${
                issue.severity === 'high'
                  ? 'bg-red-50 border-red-200 text-red-700'
                  : 'bg-amber-50 border-amber-200 text-amber-700'
              }`}>
                <span className="text-lg font-bold leading-none">{issue.contrast_ratio}</span>
                <span className="text-[10px] mt-0.5 font-medium">:1 ratio</span>
              </div>

              {/* Details */}
              <div className="flex flex-col gap-0.5">
                <p className="text-xs font-semibold text-slate-700">{issue.component}</p>
                <p className="text-xs text-slate-600">{issue.issue}</p>
                <p className="text-[11px] text-slate-400 mt-0.5">{issue.wcag_standard}</p>
              </div>

              {/* Severity pill */}
              <span className={`ml-auto shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full self-start ${
                issue.severity === 'high'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-amber-100 text-amber-700'
              }`}>
                {issue.severity.toUpperCase()}
              </span>
            </div>
          ))}

          {/* WCAG note */}
          <div className="px-4 py-2.5 bg-white/60">
            <p className="text-[11px] text-slate-400">
              Contrast is sampled per screen region. Ratios below 4.5:1 fail WCAG AA for normal text — a legal accessibility requirement in many jurisdictions.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

function ComparisonSlider({
  img1, img2, label1, label2, onClickImg1, onClickImg2,
}: {
  img1: string
  img2: string
  label1: string
  label2: string
  onClickImg1: () => void
  onClickImg2: () => void
}) {
  const [pos, setPos] = useState(50)
  const containerRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  const move = (clientX: number) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    setPos(Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100)))
  }

  return (
    <div className="flex flex-col gap-2">
      <div
        ref={containerRef}
        className="relative overflow-hidden rounded-xl border border-slate-200 shadow-sm cursor-ew-resize select-none"
        onMouseDown={e => { dragging.current = true; move(e.clientX); e.preventDefault() }}
        onMouseMove={e => { if (dragging.current) move(e.clientX) }}
        onMouseUp={() => { dragging.current = false }}
        onMouseLeave={() => { dragging.current = false }}
        onTouchStart={e => { dragging.current = true; move(e.touches[0].clientX) }}
        onTouchMove={e => { if (dragging.current) move(e.touches[0].clientX) }}
        onTouchEnd={() => { dragging.current = false }}
      >
        {/* Back: annotated live UI — always fully visible */}
        <img
          src={img2}
          alt={label2}
          className="block w-full h-auto"
          draggable={false}
          onClick={onClickImg2}
        />

        {/* Front: Figma design — clipped to left `pos`% */}
        <div
          className="absolute inset-0 overflow-hidden pointer-events-none"
          style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}
        >
          <img
            src={img1}
            alt={label1}
            className="block w-full h-auto"
            draggable={false}
          />
        </div>

        {/* Divider line */}
        <div
          className="absolute top-0 bottom-0 w-[3px] bg-white/90 shadow-[0_0_8px_rgba(0,0,0,0.5)] pointer-events-none"
          style={{ left: `${pos}%`, transform: 'translateX(-50%)' }}
        >
          {/* Handle */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white shadow-xl flex items-center justify-center text-slate-500 text-xl font-bold">
            ⇔
          </div>
        </div>

        {/* Labels */}
        <span className="absolute top-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded-md pointer-events-none">
          {label1}
        </span>
        <span className="absolute top-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded-md pointer-events-none">
          {label2}
        </span>
      </div>

      {/* Click hints */}
      <p className="text-center text-xs text-slate-400">
        Drag to compare · click either half to enlarge
      </p>
    </div>
  )
}

function ImageCard({
  label,
  src,
  accent,
  headerColor,
  badge,
  onClick,
}: {
  label: string
  src: string
  accent: string
  headerColor: string
  badge?: string
  onClick: () => void
}) {
  return (
    <div className={`flex flex-col gap-0 border rounded-xl overflow-hidden shadow-sm ${accent}`}>
      <div
        className={`relative cursor-zoom-in group ${headerColor}`}
        onClick={onClick}
      >
        <img
          src={src}
          alt={label}
          className="w-full h-44 object-cover object-top"
          onError={e => {
            (e.target as HTMLImageElement).src =
              'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
          }}
        />
        {badge && (
          <span className="absolute top-2 left-2 bg-red-600 text-white text-[10px] font-semibold px-2 py-0.5 rounded-full shadow">
            {badge}
          </span>
        )}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-white/30 backdrop-blur-[1px]">
          <span className="text-slate-800 text-xs bg-white/90 px-2 py-1 rounded shadow">
            Click to enlarge
          </span>
        </div>
      </div>
      <p className="text-xs text-slate-600 px-3 py-2 font-medium bg-white border-t border-slate-100">
        {label}
      </p>
    </div>
  )
}
