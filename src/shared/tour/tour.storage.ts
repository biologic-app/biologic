import type { TourRecord, TourStorageState } from '@/shared/tour/types'

const STORAGE_PREFIX = 'biologic:tours'
const STORAGE_VERSION = 1

function getStorageKey(userId: string) {
  return `${STORAGE_PREFIX}:${userId}`
}

function createEmptyState(): TourStorageState {
  return {
    version: STORAGE_VERSION,
    records: []
  }
}

export function readTourState(userId: string | null | undefined): TourStorageState {
  if (!userId || typeof window === 'undefined') {
    return createEmptyState()
  }

  try {
    const raw = window.localStorage.getItem(getStorageKey(userId))
    if (!raw) {
      return createEmptyState()
    }

    const parsed = JSON.parse(raw) as Partial<TourStorageState>
    return {
      version: STORAGE_VERSION,
      records: Array.isArray(parsed.records) ? parsed.records : []
    }
  } catch {
    return createEmptyState()
  }
}

export function writeTourState(userId: string | null | undefined, state: TourStorageState) {
  if (!userId || typeof window === 'undefined') {
    return
  }

  window.localStorage.setItem(getStorageKey(userId), JSON.stringify(state))
}

export function hasSeenTour(userId: string | null | undefined, key: string) {
  const state = readTourState(userId)
  return state.records.some((record) => record.key === key)
}

export function markTourSeen(userId: string | null | undefined, record: TourRecord) {
  if (!userId) {
    return
  }

  const state = readTourState(userId)
  const nextRecords = state.records.filter((item) => item.key !== record.key)
  nextRecords.push(record)

  writeTourState(userId, {
    version: STORAGE_VERSION,
    records: nextRecords
  })
}
