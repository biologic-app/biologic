import { computed } from 'vue'
import { createSharedComposable, useFetch } from '@vueuse/core'
import type { Mail } from '../types'

const _useSystemMessages = () => {
  const { data, isFetching } = useFetch('https://dashboard-template.nuxt.dev/api/mails', { initialData: [] }).json<Mail[]>()
  const mails = computed<Mail[]>(() => data.value ?? [])
  const unreadMails = computed(() => mails.value.filter(mail => mail.unread))

  function getMessageById(id: number) {
    return mails.value.find(mail => mail.id === id) ?? null
  }

  return {
    mails,
    unreadMails,
    isFetching,
    getMessageById
  }
}

export const useSystemMessages = createSharedComposable(_useSystemMessages)
