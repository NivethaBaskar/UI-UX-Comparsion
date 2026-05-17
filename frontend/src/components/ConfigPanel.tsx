import { useState } from 'react'
import type { JiraConfig } from '../types'

interface Props {
  apiKey: string
  onApiKeyChange: (v: string) => void
  jiraConfig: JiraConfig | null
  onJiraConfigChange: (v: JiraConfig | null) => void
}

export function ConfigPanel({ apiKey, onApiKeyChange, jiraConfig, onJiraConfigChange }: Props) {
  const [showKey, setShowKey] = useState(false)
  const [jiraOpen, setJiraOpen] = useState(false)
  const [jira, setJira] = useState<JiraConfig>({
    domain: '',
    email: '',
    token: '',
    project: '',
  })

  const jiraComplete = jira.domain && jira.email && jira.token && jira.project

  const handleJiraField = (field: keyof JiraConfig, value: string) => {
    const updated = { ...jira, [field]: value }
    setJira(updated)
    const complete = updated.domain && updated.email && updated.token && updated.project
    onJiraConfigChange(complete ? updated : null)
  }

  return (
    <div className="p-4 flex flex-col gap-5">
      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Configuration
        </p>

        {/* OpenAI API Key */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-slate-600">
            OpenAI API Key <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={e => onApiKeyChange(e.target.value)}
              placeholder="sk-..."
              className="input-field pr-10"
            />
            <button
              type="button"
              onClick={() => setShowKey(v => !v)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
            >
              {showKey ? 'hide' : 'show'}
            </button>
          </div>
          {apiKey && (
            <span className="text-xs text-emerald-600 flex items-center gap-1">
              <span>✓</span> Key set
            </span>
          )}
        </div>
      </div>

      {/* Jira (optional) */}
      <div className="border border-slate-200 rounded-lg overflow-hidden">
        <button
          onClick={() => setJiraOpen(v => !v)}
          className="w-full flex items-center justify-between px-3 py-2.5 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-50 transition-colors"
        >
          <span className="flex items-center gap-2">
            <span>🎫</span>
            Jira Integration
            <span className="text-xs text-slate-400 font-normal">(optional)</span>
          </span>
          <span className="text-slate-400 text-xs">{jiraOpen ? '▲' : '▼'}</span>
        </button>

        {jiraOpen && (
          <div className="px-3 pb-3 pt-1 flex flex-col gap-2.5 border-t border-slate-200 bg-slate-50/50">
            <Field
              label="Domain"
              placeholder="yourcompany.atlassian.net"
              value={jira.domain}
              onChange={v => handleJiraField('domain', v)}
            />
            <Field
              label="Email"
              placeholder="you@company.com"
              value={jira.email}
              onChange={v => handleJiraField('email', v)}
            />
            <Field
              label="API Token"
              placeholder="ATATT3xF..."
              value={jira.token}
              onChange={v => handleJiraField('token', v)}
              type="password"
            />
            <Field
              label="Project Key"
              placeholder="PROJ"
              value={jira.project}
              onChange={v => handleJiraField('project', v)}
            />

            {jiraComplete ? (
              <span className="text-xs text-emerald-600 flex items-center gap-1 mt-1">
                <span>✓</span> Jira configured
              </span>
            ) : (
              <span className="text-xs text-slate-400 mt-1">
                Fill all fields to enable ticket creation
              </span>
            )}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="mt-auto pt-4 border-t border-slate-200">
        <p className="text-xs text-slate-400 leading-relaxed">
          Images are saved in the <code className="text-slate-500 bg-slate-100 px-1 rounded">ui-ux-comparator/</code> directory.
          Existing diff and UI PNGs are deleted before each comparison run.
        </p>
      </div>
    </div>
  )
}

function Field({
  label,
  placeholder,
  value,
  onChange,
  type = 'text',
}: {
  label: string
  placeholder: string
  value: string
  onChange: (v: string) => void
  type?: string
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-slate-500">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="input-field"
      />
    </div>
  )
}
