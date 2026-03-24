import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { dateFnsLocales, intlLocales, localeOptions, nuxtUiLocales, setAppLocale, type AppLocale } from '../i18n'

export function useLocale() {
  const { locale } = useI18n()

  const currentLocale = computed<AppLocale>({
    get: () => locale.value as AppLocale,
    set: value => setAppLocale(value)
  })

  return {
    locale: currentLocale,
    localeOptions,
    nuxtUiLocale: computed(() => nuxtUiLocales[currentLocale.value]),
    dateFnsLocale: computed(() => dateFnsLocales[currentLocale.value]),
    intlLocale: computed(() => intlLocales[currentLocale.value]),
    setLocale: setAppLocale
  }
}
