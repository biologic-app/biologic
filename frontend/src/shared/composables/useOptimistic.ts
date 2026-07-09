import type { Ref } from 'vue'
import { clone } from '@/shared/utils/clone'

const cloneList = <T>(list: T[]) => clone(list)

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
