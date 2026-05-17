import type { LogEntry } from '../types'

type StepStatus = 'pending' | 'running' | 'done' | 'error'

interface Step {
  id: string
  label: string
  status: StepStatus
}

interface BpGroup {
  bp: string
  steps: Step[]
}

// ── Status derivation ─────────────────────────────────────────────────────────

function pick(
  logs: LogEntry[],
  startFrag: string,
  doneFrag: string,
  errorFrag?: string
): StepStatus {
  const msgs = logs.map(l => l.message)
  if (errorFrag && msgs.some(m => m.includes(errorFrag))) return 'error'
  if (msgs.some(m => m.includes(doneFrag)))  return 'done'
  if (msgs.some(m => m.includes(startFrag))) return 'running'
  return 'pending'
}

function deriveSteps(logs: LogEntry[], breakpoints: string[], mode: string) {
  const cleanup: Step = {
    id: 'cleanup',
    label: 'Delete old files',
    status: pick(logs, 'Deleting existing', 'Cleaned up'),
  }

  const bpGroups: BpGroup[] = breakpoints.map(bp => {
    const t = `[${bp}]`
    const screenshot: Step = {
      id: `${bp}-ss`,
      label: 'Screenshot',
      status: pick(logs, `${t} Capturing`, `${t} Screenshot saved`, `${t} Screenshot failed`),
    }
    const diff: Step = {
      id: `${bp}-diff`,
      label: 'Pixel diff',
      status: pick(logs, `${t} Generating pixel`, `${t} Diff complete`, `${t} Diff generation failed`),
    }

    if (mode === 'autogen') {
      const agent1: Step = {
        id: `${bp}-ag1`,
        label: 'AnalysisAgent',
        status: pick(logs, `${t} Starting 3-agent`, `Agent 2`, `${t} AutoGen pipeline failed`),
      }
      const agent2: Step = {
        id: `${bp}-ag2`,
        label: 'CritiqueAgent',
        status: pick(logs, `Agent 2 (CritiqueAgent)`, `Agent 3`, `${t} AutoGen pipeline failed`),
      }
      const agent3: Step = {
        id: `${bp}-ag3`,
        label: 'SeverityAgent',
        status: pick(logs, `Agent 3 (SeverityAgent)`, `${t} AutoGen complete`, `${t} AutoGen pipeline failed`),
      }
      return { bp, steps: [screenshot, diff, agent1, agent2, agent3] }
    }

    const analysis: Step = {
      id: `${bp}-llm`,
      label: 'GPT-4o vision',
      status: pick(logs, `${t} Running GPT-4o`, `${t} Found`, `${t} Analysis failed`),
    }
    const enrich: Step = {
      id: `${bp}-enrich`,
      label: 'Enrich issues',
      status: pick(logs, `${t} Enriching issues`, `${t} Enrichment done`, `${t} Enrichment failed`),
    }
    return { bp, steps: [screenshot, diff, analysis, enrich] }
  })

  return { cleanup, bpGroups }
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  logs: LogEntry[]
  breakpoints: string[]
  mode: 'classic' | 'autogen'
  isRunning: boolean
}

export function StepsPanel({ logs, breakpoints, mode, isRunning }: Props) {
  const { cleanup, bpGroups } = deriveSteps(logs, breakpoints, mode)

  const totalSteps = 1 + bpGroups.reduce((s, g) => s + g.steps.length, 0)
  const doneSteps =
    (cleanup.status === 'done' ? 1 : 0) +
    bpGroups.reduce(
      (s, g) => s + g.steps.filter(st => st.status === 'done').length,
      0
    )

  const pct = totalSteps > 0 ? Math.round((doneSteps / totalSteps) * 100) : 0

  return (
    <div className="card p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-base">⚙️</span>
          <h3 className="text-sm font-semibold text-slate-800">Analysis Progress</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">{doneSteps}/{totalSteps} steps</span>
          {isRunning && (
            <span className="flex items-center gap-1.5 text-xs text-indigo-600 font-medium">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
              Running
            </span>
          )}
          {!isRunning && doneSteps === totalSteps && totalSteps > 0 && (
            <span className="text-xs text-emerald-600 font-medium">✓ Complete</span>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Cleanup row */}
      <div className="flex items-center gap-3">
        <StepIcon status={cleanup.status} />
        <span className={`text-xs font-medium ${statusTextColor(cleanup.status)}`}>
          {cleanup.label}
        </span>
        {cleanup.status === 'running' && (
          <span className="text-xs text-slate-400 italic">in progress...</span>
        )}
      </div>

      {/* Per-breakpoint groups */}
      <div className="flex flex-col gap-3">
        {bpGroups.map(({ bp, steps }) => (
          <div key={bp} className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <BpIcon bp={bp} />
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                {bp}
              </span>
            </div>
            {/* Step chips row */}
            <div className="flex flex-wrap items-center gap-1.5 pl-5">
              {steps.map((step, i) => (
                <div key={step.id} className="flex items-center gap-1.5">
                  <StepChip step={step} />
                  {i < steps.length - 1 && (
                    <span className="text-slate-300 text-xs select-none">→</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StepIcon({ status }: { status: StepStatus }) {
  if (status === 'done') {
    return (
      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 text-xs font-bold shrink-0">
        ✓
      </span>
    )
  }
  if (status === 'error') {
    return (
      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-red-100 text-red-600 text-xs font-bold shrink-0">
        ✗
      </span>
    )
  }
  if (status === 'running') {
    return (
      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 shrink-0">
        <span className="inline-block w-3 h-3 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
      </span>
    )
  }
  return (
    <span className="flex items-center justify-center w-5 h-5 rounded-full border-2 border-slate-200 shrink-0" />
  )
}

function StepChip({ step }: { step: Step }) {
  const base = 'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors'
  const variants: Record<StepStatus, string> = {
    pending: 'bg-slate-50 text-slate-400 border-slate-200',
    running: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    done:    'bg-emerald-50 text-emerald-700 border-emerald-200',
    error:   'bg-red-50 text-red-700 border-red-200',
  }

  return (
    <span className={`${base} ${variants[step.status]}`}>
      {step.status === 'running' && (
        <span className="inline-block w-2.5 h-2.5 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin shrink-0" />
      )}
      {step.status === 'done'    && <span className="text-emerald-500">✓</span>}
      {step.status === 'error'   && <span className="text-red-500">✗</span>}
      {step.status === 'pending' && <span className="w-2 h-2 rounded-full bg-slate-300 shrink-0" />}
      {step.label}
    </span>
  )
}

function BpIcon({ bp }: { bp: string }) {
  if (bp.includes('Mobile')) return <span className="text-sm">📱</span>
  if (bp.includes('Tablet')) return <span className="text-sm">💻</span>
  return <span className="text-sm">🖥️</span>
}

function statusTextColor(status: StepStatus) {
  if (status === 'done')    return 'text-emerald-700'
  if (status === 'error')   return 'text-red-600'
  if (status === 'running') return 'text-indigo-700'
  return 'text-slate-400'
}
