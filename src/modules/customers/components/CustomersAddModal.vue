<script setup lang="ts">
import { computed, ref, reactive } from "vue";
import * as z from "zod";
import type { FormSubmitEvent } from "@nuxt/ui";
import { useI18n } from "vue-i18n";

const { t } = useI18n();

type Schema = {
  name: string;
  email: string;
};

const schema = computed(() =>
  z.object({
    name: z.string().min(2, t("validation.tooShort")),
    email: z.string().email(t("validation.invalidEmail")),
  }),
);
const open = ref(false);

const state = reactive<Partial<Schema>>({
  name: "",
  email: "",
});

const toast = useToast();
async function onSubmit(event: FormSubmitEvent<Schema>) {
  toast.add({
    title: t("common.success"),
    description: t("validation.customerAdded", { name: event.data.name }),
    color: "success",
  });
  open.value = false;
}
</script>

<template>
  <UModal
    v-model:open="open"
    :title="t('customers.create.title')"
    :description="t('customers.create.description')"
  >
    <slot></slot>
    <template #body>
      <UForm
        :schema="schema"
        :state="state"
        class="space-y-4"
        @submit="onSubmit"
      >
        <UFormField
          :label="t('customers.create.name')"
          placeholder="John Doe"
          name="name"
        >
          <UInput v-model="state.name" class="w-full" />
        </UFormField>
        <UFormField
          :label="t('customers.create.email')"
          placeholder="john.doe@example.com"
          name="email"
        >
          <UInput v-model="state.email" class="w-full" />
        </UFormField>
        <div class="flex justify-end gap-2">
          <UButton
            :label="t('common.cancel')"
            color="neutral"
            variant="subtle"
            @click="open = false"
          />
          <UButton
            :label="t('common.create')"
            color="primary"
            variant="solid"
            type="submit"
          />
        </div>
      </UForm>
    </template>
  </UModal>
</template>
