export interface LogEntry {
  message: string
  level: 'info' | 'success' | 'error' | 'agent'
  ts: number
}

export interface BBox {
  x: number
  y: number
  w: number
  h: number
}

export interface Issue {
  type: string
  component: string
  issue: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  root_cause?: string
  suggested_fix?: string
  team?: string
  confidence?: number
  jira_title?: string
  breakpoint?: string
  bbox?: BBox
}

export interface BreakpointResult {
  issues: Issue[]
  mismatch_pct: number
  ui_image: string
  annotated_image: string
  diff_image: string
  figma_image: string
}

export interface ConvLogEntry {
  agent: string
  content: string
}

export interface CompareResult {
  breakpoints: Record<string, BreakpointResult>
  conversation_log: ConvLogEntry[]
}

export interface JiraConfig {
  domain: string
  email: string
  token: string
  project: string
}

export const ALL_BREAKPOINTS = [
  'Desktop (1440px)',
  'Tablet (768px)',
  'Mobile (375px)',
] as const

export const BP_SUFFIX: Record<string, string> = {
  'Mobile (375px)':   '375',
  'Tablet (768px)':   '768',
  'Desktop (1440px)': '1440',
}
