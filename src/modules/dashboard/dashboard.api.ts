import { apiRequest } from '@/shared/api/client.api'
import type { DashboardSummary, Period, Range } from '@/modules/dashboard/types'

interface DashboardSummaryResponse {
  data: DashboardSummary
  meta: {
    timestamp: string
    version: string
    operation: string | null
  }
}

const toApiDate = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export const loadDashboardSummary = async (
  range: Range,
  period: Period
): Promise<DashboardSummary> => {
  const response = await apiRequest<DashboardSummaryResponse>('/dashboard/summary', {
    method: 'GET',
    params: {
      date_from: toApiDate(range.start),
      date_to: toApiDate(range.end),
      period
    }
  })

  return response.data
}
