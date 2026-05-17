import * as XLSX from 'xlsx'
import type { Issue } from '../types'

const SEV_BADGE: Record<string, string> = {
  critical: 'bg-red-50 text-red-700 border border-red-200',
  high:     'bg-orange-50 text-orange-700 border border-orange-200',
  medium:   'bg-amber-50 text-amber-700 border border-amber-200',
  low:      'bg-green-50 text-green-700 border border-green-200',
}

const TYPE_BADGE: Record<string, string> = {
  alignment: 'bg-blue-50 text-blue-700',
  spacing:   'bg-cyan-50 text-cyan-700',
  color:     'bg-pink-50 text-pink-700',
  font:      'bg-violet-50 text-violet-700',
  missing:   'bg-red-50 text-red-700',
}

interface Props {
  issues: Issue[]
  onDownload: () => void
  filename?: string
}

function downloadExcel(issues: Issue[], filename: string) {
  const rows = issues.map(issue => ({
    Severity:      issue.severity ?? '',
    Type:          issue.type ?? '',
    Component:     issue.component ?? '',
    'Jira Title':  issue.jira_title ?? '',
    Issue:         issue.issue ?? '',
    Team:          issue.team ?? '',
    'Root Cause':  issue.root_cause ?? '',
    'Suggested Fix': issue.suggested_fix ?? '',
    'Confidence %': issue.confidence ?? '',
    Breakpoint:    issue.breakpoint ?? '',
  }))
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'UI Issues')
  XLSX.writeFile(wb, filename)
}

export function IssueTable({ issues, onDownload, filename = 'ui-issues' }: Props) {
  const header = (
    <div className="flex items-center justify-between">
      <span className="text-sm text-slate-500">
        <span className="font-semibold text-slate-800">{issues.length}</span> issue
        {issues.length !== 1 ? 's' : ''} detected
      </span>
      <div className="flex items-center gap-2">
        <button onClick={onDownload} className="btn-ghost text-xs flex items-center gap-1.5">
          <span>⬇</span>
          JSON
        </button>
        <button
          onClick={() => downloadExcel(issues, `${filename}.xlsx`)}
          className="btn-ghost text-xs flex items-center gap-1.5 text-emerald-700 hover:bg-emerald-50"
        >
          <span>⬇</span>
          Excel
        </button>
      </div>
    </div>
  )

  if (issues.length === 0) {
    return (
      <div className="flex flex-col gap-3">
        {header}
        <div className="text-center py-10 text-slate-400 text-sm">
          No issues detected for this breakpoint.
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {header}

      {/* Severity summary */}
      <SeveritySummary issues={issues} />

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 shadow-sm">
        <table className="w-full text-sm min-w-[900px]">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <Th>Severity</Th>
              <Th>Type</Th>
              <Th>Component</Th>
              <Th width="w-64">Jira Title / Issue</Th>
              <Th>Team</Th>
              <Th>Root Cause</Th>
              <Th>Suggested Fix</Th>
              <Th>Conf.</Th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue, i) => (
              <tr
                key={i}
                className={`border-b border-slate-100 ${
                  i % 2 === 0 ? 'bg-white' : 'bg-slate-50/60'
                } hover:bg-indigo-50/30 transition-colors`}
              >
                <td className="px-3 py-2.5 whitespace-nowrap">
                  <span
                    className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      SEV_BADGE[issue.severity?.toLowerCase()] ?? 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {issue.severity?.toUpperCase()}
                  </span>
                </td>
                <td className="px-3 py-2.5 whitespace-nowrap">
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded ${
                      TYPE_BADGE[issue.type?.toLowerCase()] ?? 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {issue.type}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-slate-600 whitespace-nowrap font-mono text-xs">
                  {issue.component}
                </td>
                <td className="px-3 py-2.5 text-slate-800 max-w-xs">
                  <p className="font-medium text-xs leading-snug">
                    {issue.jira_title || issue.issue}
                  </p>
                  {issue.jira_title && issue.issue && (
                    <p className="text-slate-400 text-xs mt-0.5">{issue.issue}</p>
                  )}
                </td>
                <td className="px-3 py-2.5 text-slate-500 whitespace-nowrap text-xs">
                  {issue.team ?? '—'}
                </td>
                <td className="px-3 py-2.5 text-slate-500 text-xs max-w-[200px]">
                  <span className="line-clamp-2">{issue.root_cause ?? '—'}</span>
                </td>
                <td className="px-3 py-2.5 text-slate-500 text-xs max-w-[200px]">
                  <span className="line-clamp-2">{issue.suggested_fix ?? '—'}</span>
                </td>
                <td className="px-3 py-2.5 text-xs text-center whitespace-nowrap">
                  {issue.confidence != null ? (
                    <span
                      className={
                        issue.confidence >= 75
                          ? 'text-emerald-600 font-medium'
                          : issue.confidence >= 50
                          ? 'text-amber-600 font-medium'
                          : 'text-red-500 font-medium'
                      }
                    >
                      {issue.confidence}%
                    </span>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Th({ children, width }: { children: React.ReactNode; width?: string }) {
  return (
    <th
      className={`px-3 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider ${width ?? ''}`}
    >
      {children}
    </th>
  )
}

function SeveritySummary({ issues }: { issues: Issue[] }) {
  const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 }
  for (const issue of issues) {
    const sev = issue.severity?.toLowerCase() ?? 'low'
    counts[sev] = (counts[sev] ?? 0) + 1
  }

  return (
    <div className="flex gap-2 flex-wrap">
      {Object.entries(counts).map(([sev, count]) =>
        count > 0 ? (
          <div
            key={sev}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium ${
              SEV_BADGE[sev] ?? 'bg-slate-100 text-slate-600'
            }`}
          >
            <span className="font-bold">{count}</span>
            <span className="opacity-75">{sev}</span>
          </div>
        ) : null
      )}
    </div>
  )
}
