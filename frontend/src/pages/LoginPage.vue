<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import * as z from "zod";
import type { FormSubmitEvent } from "@nuxt/ui";
import { useI18n } from "vue-i18n";
import { LoginControls, LoginHero, useAuth } from "@/modules/auth";
import { userModeList } from "@/shared/config/user-modes";
import type { ApiError } from "@/shared/types/api";

const auth = useAuth();
const router = useRouter();
const toast = useToast();
const { t } = useI18n();
const showPassword = ref(false);

const state = reactive({ username: "", password: "", remember: false });

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
    await auth.login(username, password, payload.data.remember);
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

const roleItems = computed(() =>
  userModeList.map((mode) => ({
    label: t(mode.labelKey),
    icon: mode.icon,
    async onSelect() {
      try {
        await auth.loginAs(mode.id);
        await router.push({ name: "dashboard" });
        toast.add({
          title: t("common.success"),
          description: t("login.successDescription", { username: mode.id }),
          color: "success",
          icon: "i-lucide-circle-check",
        });
      } catch {
        toast.add({
          title: t("login.errorTitle"),
          description: t("login.errorDescription"),
          color: "error",
          icon: "i-lucide-circle-alert",
        });
      }
    },
  })),
);
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

          <UForm
            :schema="schema"
            :state="state"
            class="space-y-4"
            @submit="onSubmit($event)"
          >
            <UFormField name="username" :label="t('login.username')">
              <UInput
                v-model="state.username"
                :placeholder="t('login.usernamePlaceholder')"
                icon="i-lucide-user-round"
                autocomplete="username"
                size="md"
                class="w-full"
              />
            </UFormField>

            <UFormField name="password" :label="t('login.password')">
              <UInput
                v-model="state.password"
                :type="showPassword ? 'text' : 'password'"
                :placeholder="t('login.passwordPlaceholder')"
                icon="i-lucide-lock"
                autocomplete="current-password"
                size="md"
                class="w-full"
              />
            </UFormField>

            <UFormField name="remember">
              <UCheckbox
                v-model="state.remember"
                :label="t('login.remember')"
                :description="t('login.rememberHint')"
              />
            </UFormField>

            <UFieldGroup size="xl" class="w-full">
              <UButton
                type="submit"
                :label="t('login.submit')"
                class="flex-1"
                :loading="auth.loading"
              />
              <UDropdownMenu
                :items="roleItems"
                :content="{ align: 'end', side: 'top' }"
              >
                <UButton
                  color="neutral"
                  variant="outline"
                  icon="i-lucide-chevron-down"
                  :disabled="auth.loading"
                  aria-label="Войти как роль"
                />
              </UDropdownMenu>
            </UFieldGroup>
          </UForm>
        </UPageCard>
      </div>
    </section>
  </div>
</template>
