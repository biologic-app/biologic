const isClient = typeof window !== 'undefined'

export const readJson = <T>(key: string, fallback: T): T => {
  if (!isClient) return fallback
  try {
    const raw = localStorage.getItem(key)
    return raw !== null ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

export const writeJson = <T>(key: string, value: T): void => {
  if (!isClient) return
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Ignore: private mode or storage full — callers should still work.
  }
}
