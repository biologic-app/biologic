// composables/useJournalUser.ts
// «Личность» текущего сотрудника для атрибуции действий в журналах.
// По умолчанию берём ФИО из реальной аутентификации (useAuth), но допускаем
// ручной override в localStorage — это удобно, чтобы сымитировать передачу
// записи другому сотруднику прямо в прототипе журналов.
import { computed, ref } from 'vue'
import { useAuth } from '@/modules/auth'

const KEY = 'journal-current-user'
const override = ref<string>('')
let inited = false

function ensureInit() {
  if (inited || typeof window === 'undefined') {
    return
  }
  override.value = localStorage.getItem(KEY) ?? ''
  inited = true
}

export function useJournalUser() {
  ensureInit()

  const auth = useAuth()

  // Эффективное имя: ручной override приоритетнее ФИО из auth.
  const current = computed<string>(
    () => override.value.trim() || auth.user?.fullName?.trim() || '',
  )

  function setUser(name: string) {
    override.value = name.trim()
    if (typeof window !== 'undefined') {
      localStorage.setItem(KEY, override.value)
    }
  }

  // Имя для подписи действий: реальное или запасное «Аноним».
  function authorName(): string {
    return current.value || 'Аноним'
  }

  return { current, override, setUser, authorName }
}
