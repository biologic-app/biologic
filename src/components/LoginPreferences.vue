<script setup lang="ts">
import { computed } from 'vue'
import { en as nuxtUiEn, ru as nuxtUiRu } from '@nuxt/ui/locale'
import { useColorMode } from '@vueuse/core'
import { useI18n } from 'vue-i18n'
import { useLocale } from '../composables/useLocale'
import type { TabsItem } from '@nuxt/ui'

const colorMode = useColorMode()
const { t } = useI18n()
const { locale } = useLocale()

const locales = [nuxtUiRu, nuxtUiEn]

type ThemeMode = 'light' | 'dark'

const themeOptions = computed<TabsItem[]>(() => [
  {
    label: t('userMenu.light'),
    icon: 'i-lucide-sun',
    value: 'light'
  },
  {
    label: t('userMenu.dark'),
    icon: 'i-lucide-moon',
    value: 'dark'
  }
])

const themeMode = computed<ThemeMode>({
  get: () => colorMode.value === 'dark' ? 'dark' : 'light',
  set: value => {
    colorMode.value = value
  }
})
</script>

<template>
  <div class="inline-flex w-full flex-col gap-3 rounded-2xl border border-default/70 bg-default/85 p-2 shadow-lg backdrop-blur sm:w-auto sm:min-w-[22rem] sm:flex-row sm:items-end sm:gap-2">
    <div class="space-y-1 sm:flex-1 min-w-56">
      <p class="px-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">
        {{ t('userMenu.theme') }}
      </p>
      <UTabs
        v-model="themeMode"
        :items="themeOptions"
        size="xs"
        color="neutral"
        variant="pill"
        :content="false"
        class="w-full"
        :ui="{
          list: 'w-full rounded-xl bg-elevated/80 p-1 ring ring-default/60',
          trigger: 'flex-1 justify-center'
        }"
      />
    </div>

    <div class="space-y-1 ">
      <p class="px-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">
        {{ t('app.language') }}
      </p>
      <ULocaleSelect
        v-model="locale"
        :locales="locales"
        color="neutral"
        variant="none"
        :search-input="false"
        :content="{ align: 'end', collisionPadding: 16 }"
        :ui="{
          base: 'rounded-xl bg-elevated/80 px-3 ring ring-default/60',
          value: 'font-medium text-default',
          trailingIcon: 'text-muted'
        }"
      />
    </div>
  </div>
</template>
