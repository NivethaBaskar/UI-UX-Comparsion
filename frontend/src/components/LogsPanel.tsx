import { useEffect, useRef } from 'react'
import type { LogEntry } from '../types'

const LEVEL_STYLE: Record<string, string> = {
  info:    'text-slate-700',
  success: 'text-emerald-700',
  error:   'text-red-600',
  agent:   'text-violet-700',
}

const LEVEL_PREFIX: Record<string, string> = {
  info:    '·',
  success: '✓',
  error:   '✗',
  agent:   '⬡',
}

function formatTs(ts: number) {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString(undefined, { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

interface Props {
  logs: LogEntry[]
  isRunning: boolean
}

export function LogsPanel({ logs, isRunning }: Props) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-200 bg-slate-50 shrink-0">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Agent Process Trace
        </span>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="text-emerald-600">✓ success</span>
          <span className="text-red-500">✗ error</span>
          <span className="text-violet-600">⬡ agent</span>
          <span>{logs.length} events</span>
          {isRunning && (
            <span className="flex items-center gap-1 text-indigo-600">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
              live
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-slate-50 p-3 font-mono text-xs leading-relaxed border-t border-slate-100">
        {logs.length === 0 ? (
          <p className="text-slate-400 text-center mt-8">
            Logs will stream here when comparison starts.
          </p>
        ) : (
          <>
            {logs.map((entry, i) => (
              <div
                key={i}
                className={`flex items-start gap-2 py-0.5 ${LEVEL_STYLE[entry.level] ?? 'text-slate-600'}`}
              >
                <span className="text-slate-300 shrink-0 select-none">{formatTs(entry.ts)}</span>
                <span className="shrink-0 w-3 select-none">{LEVEL_PREFIX[entry.level] ?? '·'}</span>
                <span className="break-all">{entry.message}</span>
              </div>
            ))}
            {isRunning && (
              <div className="flex items-center gap-2 text-indigo-500 py-0.5 mt-1">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
                <span className="italic text-indigo-400">waiting for next step...</span>
              </div>
            )}
          </>
        )}
        <div ref={endRef} />
      </div>
    </div>
  )
}
