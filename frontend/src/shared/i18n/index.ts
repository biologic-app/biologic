import { createI18n } from 'vue-i18n'
import { en as nuxtUiEn, ru as nuxtUiRu } from '@nuxt/ui/locale'
import { enUS, ru as dateFnsRu } from 'date-fns/locale'
import { messages } from '@/shared/i18n/messages'

export type AppLocale = 'ru' | 'en'

const STORAGE_KEY = 'biologic-lims-locale'

export const localeOptions = [
  { label: 'Русский', value: 'ru' },
  { label: 'English', value: 'en' }
] as const satisfies ReadonlyArray<{ label: string, value: AppLocale }>

export const nuxtUiLocales = {
  ru: nuxtUiRu,
  en: nuxtUiEn
} as const

export const dateFnsLocales = {
  ru: dateFnsRu,
  en: enUS
} as const

export const intlLocales = {
  ru: 'ru-RU',
  en: 'en-US'
} as const

function resolveInitialLocale(): AppLocale {
  if (typeof window === 'undefined') {
    return 'ru'
  }

  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'ru' || stored === 'en') {
    return stored
  }

  return window.navigator.language.toLowerCase().startsWith('en') ? 'en' : 'ru'
}

function syncDocumentLocale(locale: AppLocale) {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale
  }
}

const initialLocale = resolveInitialLocale()
syncDocumentLocale(initialLocale)

// Russian has a 3-form plural (one/few/many: 1 образец, 2 образца, 5 образцов)
// that vue-i18n's built-in rule doesn't cover — messages with 3 pipe-separated
// forms for `ru` rely on this custom rule to pick the right index.
function ruPluralRule(choice: number): number {
  const mod10 = choice % 10
  const mod100 = choice % 100
  if (mod10 === 1 && mod100 !== 11) return 0
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return 1
  return 2
}

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: 'en',
  messages,
  globalInjection: true,
  pluralRules: {
    ru: ruPluralRule
  }
})

export function setAppLocale(locale: AppLocale) {
  i18n.global.locale.value = locale
  syncDocumentLocale(locale)

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, locale)
  }
}
