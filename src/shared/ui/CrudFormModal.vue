<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { FormField } from '@/shared/types/form'
import { fromDateTimeLocalValue, toDateTimeLocalValue } from '@/shared/utils/format'

const props = defineProps<{
  open: boolean
  title: string
  fields: FormField[]
  item: Record<string, any> | null
  mode: 'view' | 'edit' | 'create'
  loading?: boolean
  readOnly?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'save', payload: Record<string, any>): void
}>()

const formRef = ref<HTMLFormElement | null>(null)
const form = reactive<Record<string, any>>({})

const normalizedFields = computed(() =>
  props.fields.map((field) => ({
    ...field,
    type: field.type || 'text'
  }))
)

const resetForm = () => {
  normalizedFields.value.forEach((field) => {
    if (field.type === 'boolean') {
      form[field.key] = false
      return
    }

    if (field.type === 'file') {
      form[field.key] = null
      return
    }

    form[field.key] = ''
  })
}

watch(
  () => [props.item, props.open, props.fields] as const,
  () => {
    resetForm()

    if (!props.item) {
      return
    }

    normalizedFields.value.forEach((field) => {
      const value = props.item?.[field.key]
      if (field.type === 'boolean') {
        form[field.key] = Boolean(value)
        return
      }

      if (field.type === 'date') {
        form[field.key] = toDateTimeLocalValue(value)
        return
      }

      form[field.key] = value ?? ''
    })
  },
  { immediate: true, deep: true }
)

const close = () => {
  emit('update:open', false)
}

const submit = () => {
  if (formRef.value && !formRef.value.reportValidity()) {
    return
  }

  const payload: Record<string, any> = {}

  normalizedFields.value.forEach((field) => {
    if (field.type === 'file') {
      payload[field.key] = form[field.key] || null
      return
    }

    if (field.type === 'date') {
      payload[field.key] = fromDateTimeLocalValue(form[field.key])
      return
    }

    if (field.type === 'number') {
      payload[field.key] = form[field.key] === '' ? null : Number(form[field.key])
      return
    }

    if (field.type === 'boolean') {
      payload[field.key] = Boolean(form[field.key])
      return
    }

    payload[field.key] = form[field.key] === '' ? null : form[field.key]
  })

  emit('save', payload)
}

const onFileChange = (key: string, event: Event) => {
  const input = event.target as HTMLInputElement
  form[key] = input.files?.[0] || null
}
</script>

<template>
  <UModal
    :open="open"
    :title="title"
    :dismissible="!loading"
    :ui="{ content: 'max-w-3xl' }"
    @update:open="emit('update:open', $event)"
  >
    <template #body>
      <form ref="formRef" class="grid gap-4 md:grid-cols-2" @submit.prevent="submit">
        <div
          v-for="field in normalizedFields"
          :key="field.key"
          class="grid gap-2"
          :class="field.type === 'textarea' ? 'md:col-span-2' : ''"
        >
          <label :for="field.key" class="text-sm font-medium text-toned">
            {{ field.label }}
          </label>

          <UCheckbox
            v-if="field.type === 'boolean'"
            v-model="form[field.key]"
            :label="field.label"
            :disabled="readOnly"
          />

          <UTextarea
            v-else-if="field.type === 'textarea'"
            :id="field.key"
            v-model="form[field.key]"
            autoresize
            :rows="4"
            :required="field.required"
            :placeholder="field.placeholder"
            :disabled="readOnly"
          />

          <USelectMenu
            v-else-if="field.type === 'select'"
            :id="field.key"
            v-model="form[field.key]"
            :items="field.options || []"
            value-key="value"
            label-key="label"
            :search-input="{ placeholder: 'Поиск' }"
            :required="field.required"
            :disabled="readOnly"
            clear
          />

          <UInput
            v-else-if="field.type === 'date'"
            :id="field.key"
            v-model="form[field.key]"
            type="datetime-local"
            :required="field.required"
            :disabled="readOnly"
          />

          <UInput
            v-else-if="field.type === 'file'"
            :id="field.key"
            type="file"
            :accept="field.accept"
            :required="field.required"
            :disabled="readOnly"
            @change="onFileChange(field.key, $event)"
          />

          <UInput
            v-else
            :id="field.key"
            v-model="form[field.key]"
            :type="field.type === 'number' ? 'number' : 'text'"
            :required="field.required"
            :placeholder="field.placeholder"
            :disabled="readOnly"
          />
        </div>
      </form>
    </template>

    <template #footer>
      <div class="flex w-full items-center justify-end gap-3">
        <UButton color="neutral" variant="ghost" label="Закрыть" :disabled="loading" @click="close" />
        <UButton
          v-if="!readOnly"
          color="primary"
          :loading="loading"
          label="Сохранить"
          icon="i-lucide-save"
          @click="submit"
        />
      </div>
    </template>
  </UModal>
</template>
