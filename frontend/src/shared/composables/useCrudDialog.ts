import { computed, ref } from 'vue'
import { usePermission } from '@/shared/composables/usePermission'
import type { Resource } from '@/shared/types/permissions'

export type CrudMode = 'view' | 'edit' | 'create'

export const useCrudDialog = <T>(resource: Resource) => {
  const visible = ref(false)
  const mode = ref<CrudMode>('view')
  const selected = ref<T | null>(null)
  const { can } = usePermission()

  const openView = (row: T) => {
    selected.value = row
    mode.value = 'view'
    visible.value = true
  }

  const openEdit = (row: T) => {
    if (!can(resource, 'edit')) {
      openView(row)
      return
    }

    selected.value = row
    mode.value = 'edit'
    visible.value = true
  }

  const openCreate = () => {
    mode.value = 'create'
    selected.value = null
    visible.value = true
  }

  const close = () => {
    visible.value = false
  }

  const startEdit = () => {
    mode.value = 'edit'
  }

  const readOnly = computed(() => {
    if (mode.value === 'create') {
      return !can(resource, 'create')
    }

    if (mode.value === 'edit') {
      return !can(resource, 'edit')
    }

    return true
  })

  return {
    visible,
    mode,
    selected,
    readOnly,
    openView,
    openEdit,
    openCreate,
    close,
    startEdit
  }
}
