import { createFetch } from '@vueuse/core'

const apiUrl = import.meta.env.VITE_API_URL 


export const useApi = createFetch({
  baseUrl: apiUrl,
  options: {
    async beforeFetch({ options }) {
      options.credentials = 'include'
      return { options }
    }
  }
})
