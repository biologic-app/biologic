import type { Ref } from 'vue'

const cloneList = <T>(list: T[]) => JSON.parse(JSON.stringify(list)) as T[]

export const useOptimistic = <T extends { id: number | string }>() => {
  const snapshot = { current: null as T[] | null }

  const takeSnapshot = (list: T[]) => {
    snapshot.current = cloneList(list)
  }

  const rollback = (target: Ref<T[]>) => {
    if (snapshot.current) {
      target.value = snapshot.current
      snapshot.current = null
    }
  }

  const updateItem = (target: Ref<T[]>, updated: T) => {
    takeSnapshot(target.value)
    target.value = target.value.map((item) => (item.id === updated.id ? { ...item, ...updated } : item))
    return () => rollback(target)
  }

  const removeItem = (target: Ref<T[]>, id: number | string) => {
    takeSnapshot(target.value)
    target.value = target.value.filter((item) => item.id !== id)
    return () => rollback(target)
  }

  return {
    updateItem,
    removeItem,
    rollback
  }
}
