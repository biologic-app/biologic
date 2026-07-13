export type Period = 'daily' | 'weekly' | 'monthly'

export interface Range {
  start: Date
  end: Date
}

export interface Stat {
  title: string
  icon: string
  value: number | string
  variation: number
  formatter?: (value: number) => string
}

export interface DashboardKpi {
  key: string
  label: string
  value: number
  unit: 'count' | 'minutes' | string
  icon?: string
}

export interface DashboardTimelineItem {
  bucket_start: string
  directions_received: number
  samples_received: number
  samples_completed: number
  samples_rejected: number
  research_completed: number
  tests_completed: number
  tests_rejected: number
  protocols_issued: number
}

export interface DashboardStatusItem {
  status_code: string | null
  status_color: string | null
  count: number
}

export interface DashboardLabItem {
  lab_id: string | null
  lab_name: string
  active_count: number
  completed_count: number
}

export interface DashboardSampleTypeItem {
  sample_type_id: string | null
  sample_type_name: string
  count: number
}

export interface DashboardSummary {
  period: Period
  date_from: string
  date_to: string
  updated_at: string | null
  kpis: DashboardKpi[]
  timeline: DashboardTimelineItem[]
  samples_by_status: DashboardStatusItem[]
  research_by_lab: DashboardLabItem[]
  sample_types: DashboardSampleTypeItem[]
}
