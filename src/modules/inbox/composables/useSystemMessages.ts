import { onMounted, ref, shallowRef } from 'vue'
import { apiReadListRequest } from '@/shared/api/client.api'
import type { Mail } from '@/shared/types'

const mails = shallowRef<Mail[]>([])
const isFetching = ref(false)
const unreadMails = shallowRef<Mail[]>([])
let initialized = false

const loadMessages = async () => {
  isFetching.value = true
  try {
    const response = await apiReadListRequest<Record<string, unknown>>('/alerts', {
      method: 'GET',
      params: { limit: 100 }
    })

    mails.value = response.items.map<Mail>((item, index) => ({
      id: Number(item.id) || index + 1,
      unread: item.is_read === false || item.read_at === null || item.unread === true,
      from: {
        id: 0,
        name: String(item.sender_name || item.actor_name || 'System'),
        email: String(item.sender_email || ''),
        status: 'subscribed',
        location: String(item.source || 'Backend')
      },
      subject: String(item.title || item.type || 'System alert'),
      body: String(item.message || item.body || item.text || ''),
      date: String(item.created_at || item.updated_at || item.date || new Date().toISOString())
    }))
    unreadMails.value = mails.value.filter((mail) => mail.unread)
  } finally {
    isFetching.value = false
  }
}

export function useSystemMessages() {
  function getMessageById(id: number) {
    return mails.value.find(mail => mail.id === id) ?? null
  }

  onMounted(() => {
    if (!initialized) {
      initialized = true
      loadMessages()
    }
  })

  return {
    mails,
    unreadMails,
    isFetching,
    loadMessages,
    getMessageById
  }
}
