<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import * as z from "zod";
import type { AuthFormField, FormSubmitEvent } from "@nuxt/ui";
import { useI18n } from "vue-i18n";
import { LoginControls, LoginHero, useAuth } from "@/modules/auth";
import {} from "@/modules/auth";
import type { ApiError } from "@/shared/types/api";

const auth = useAuth();
const router = useRouter();
const toast = useToast();
const { t } = useI18n();
const showPassword = ref(false);

const fields = computed<AuthFormField[]>(() => [
  {
    name: "username",
    type: "text",
    label: t("login.username"),
    placeholder: t("login.usernamePlaceholder"),
    autocomplete: "username",
    icon: "i-lucide-user-round",
    size: "md",
  },
  {
    name: "password",
    type: showPassword.value ? "text" : "password",
    label: t("login.password"),
    placeholder: t("login.passwordPlaceholder"),
    autocomplete: "current-password",
    icon: "i-lucide-lock",
    size: "md",
  },
  {
    name: "remember",
    type: "checkbox",
    description: t("login.rememberHint"),
    label: t("login.remember"),
  },
]);

const schema = computed(() =>
  z.object({
    username: z
      .string()
      .trim()
      .min(1, { message: t("login.validation.usernameRequired") })
      .min(3, { message: t("login.validation.usernameMin") })
      .max(64, { message: t("login.validation.usernameMax") })
      .regex(/^[a-zA-Z0-9._-]+$/, {
        message: t("login.validation.usernameFormat"),
      }),
    password: z
      .string()
      .min(8, { message: t("login.validation.passwordMin") })
      .max(128, { message: t("login.validation.passwordMax") }),
    remember: z.boolean().default(false),
  }),
);

type LoginSchema = z.output<typeof schema.value>;

async function onSubmit(payload: FormSubmitEvent<LoginSchema>) {
  const username = payload.data.username.trim();
  const password = payload.data.password;

  try {
    await auth.login(username, password);
    await router.push({ name: "dashboard" });
    toast.add({
      title: t("common.success"),
      description: t("login.successDescription", { username }),
      color: "success",
      icon: "i-lucide-circle-check",
    });
  } catch (error) {
    const apiError = error as ApiError;

    toast.add({
      title: t("login.errorTitle"),
      description: apiError.message || t("login.errorDescription"),
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  }
}
</script>

<template>
  <div class="grid w-full gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
    <section class="hidden lg:block">
      <LoginHero
        :badge-text="t('login.badge')"
        :title="t('login.heroTitle')"
        :description="t('login.heroDescription')"
      />
      <div class="w-96">
        <LoginControls />
      </div>
    </section>

    <section class="mx-auto w-full max-w-md">
      <div class="space-y-4">
        <LoginControls class="lg:hidden" />

        <UPageCard
          variant="subtle"
          class="border border-default/70 bg-default/90 shadow-2xl backdrop-blur"
        >
          <div class="space-y-1 pb-4">
            <h2 class="text-2xl font-semibold text-highlighted">
              {{ t("login.title") }}
            </h2>
            <p class="text-sm text-toned">
              {{ t("login.description") }}
            </p>
          </div>

          <UAuthForm
            :schema="schema"
            :fields="fields"
            :submit="{
              label: t('login.submit'),
              size: 'xl',
              loading: auth.loading,
            }"
            @submit="onSubmit($event)"
          />
        </UPageCard>
      </div>
    </section>
  </div>
</template>
