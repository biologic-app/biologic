<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { z } from "zod";
import type { FormSubmitEvent } from "@nuxt/ui";
import { useI18n } from "vue-i18n";
import LoginPreferences from "@/modules/auth/components/LoginPreferences.vue";
import type { ApiError } from "@/shared/types/api";
import { useAuthStore } from "../auth.store";

type LoginSchema = {
  username: string;
  password: string;
  remember: boolean;
};

const auth = useAuthStore();
const router = useRouter();
const toast = useToast();
const { t } = useI18n();
const showPassword = ref(false);

const form = reactive<LoginSchema>({
  username: "",
  password: "",
  remember: false,
});

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
      .min(8)
      .max(128)
      .regex(/\d/, { message: "digit" })
      .regex(/[a-z]/, { message: "lowercase" })
      .regex(/[A-Z]/, { message: "uppercase" }),
    remember: z.boolean().default(false),
  }),
);

function checkStrength(value: string) {
  const requirements = [
    { regex: /.{8,}/, text: t("login.passwordRequirements.length") },
    { regex: /\d/, text: t("login.passwordRequirements.number") },
    { regex: /[a-z]/, text: t("login.passwordRequirements.lowercase") },
    // { regex: /[A-Z]/, text: t("login.passwordRequirements.uppercase") },
  ];

  return requirements.map((requirement) => ({
    met: requirement.regex.test(value),
    text: requirement.text,
  }));
}

const passwordStrength = computed(() => checkStrength(form.password));
const passwordScore = computed(
  () => passwordStrength.value.filter((requirement) => requirement.met).length,
);

const passwordColor = computed(
  (): "neutral" | "error" | "warning" | "success" => {
    if (passwordScore.value === 0) {
      return "neutral";
    }
    if (passwordScore.value <= 2) {
      return "error";
    }
    if (passwordScore.value === 3) {
      return "warning";
    }
    return "success";
  },
);

const passwordText = computed(() => {
  if (passwordScore.value === 0) {
    return t("login.passwordStrengthIdle");
  }
  if (passwordScore.value <= 2) {
    return t("login.passwordStrengthWeak");
  }
  if (passwordScore.value === 3) {
    return t("login.passwordStrengthMedium");
  }
  return t("login.passwordStrengthStrong");
});

async function onSubmit(event: FormSubmitEvent<LoginSchema>) {
  const username = event.data.username.trim();
  const password = event.data.password;

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
      <div class="max-w-2xl space-y-8">
        <UBadge
          :label="t('login.badge')"
          variant="subtle"
          color="primary"
          size="xl"
        />
        <div class="space-y-4">
          <h1
            class="max-w-xl text-5xl font-semibold tracking-tight text-highlighted"
          >
            {{ t("login.heroTitle") }}
          </h1>
          <p class="max-w-xl text-lg leading-8 text-toned">
            {{ t("login.heroDescription") }}
          </p>
          <LoginPreferences />
        </div>
      </div>
    </section>
    <section class="mx-auto w-full max-w-md">
      <div class="space-y-4">
        <div class="flex justify-end lg:hidden">
          <LoginPreferences />
        </div>

        <UPageCard
          variant="subtle"
          class="border border-default/70 bg-default/90 shadow-2xl backdrop-blur"
        >
          <div class="space-y-1">
            <h2 class="text-2xl font-semibold text-highlighted">
              {{ t("login.title") }}
            </h2>
            <p class="text-sm text-toned">
              {{ t("login.description") }}
            </p>
          </div>

          <UForm
            :schema="schema"
            :state="form"
            class="space-y-2"
            @submit="onSubmit"
          >
            <UFormField :label="t('login.username')" name="username">
              <UInput
                v-model="form.username"
                :placeholder="t('login.usernamePlaceholder')"
                autocomplete="username"
                icon="i-lucide-user-round"
                size="md"
                class="w-full"
              />
            </UFormField>

            <UFormField
              :label="t('login.password')"
              name="password"
              :ui="{ error: 'hidden' }"
            >
              <div class="space-y-3">
                <UInput
                  id="login-password"
                  v-model="form.password"
                  :placeholder="t('login.passwordPlaceholder')"
                  :color="passwordColor"
                  :type="showPassword ? 'text' : 'password'"
                  :aria-invalid="passwordScore < 4"
                  aria-describedby="login-password-strength"
                  autocomplete="current-password"
                  icon="i-lucide-lock"
                  size="md"
                  :ui="{ trailing: 'pe-1' }"
                  class="w-full"
                >
                  <template #trailing>
                    <UButton
                      type="button"
                      color="neutral"
                      variant="link"
                      size="sm"
                      :icon="showPassword ? 'i-lucide-eye-off' : 'i-lucide-eye'"
                      @click="showPassword = !showPassword"
                    />
                  </template>
                </UInput>
              </div>
            </UFormField>
            <div class="rounded-2xl border border-default/70 bg-muted/40 p-4">
              <div class="space-y-3">
                <UProgress
                  :color="passwordColor"
                  :indicator="passwordText"
                  :model-value="passwordScore"
                  :max="4"
                  size="sm"
                />

                <p
                  id="login-password-strength"
                  class="text-sm font-medium text-highlighted"
                >
                  {{ passwordText }}.
                  {{ t("login.passwordRequirementsTitle") }}
                </p>

                <ul
                  class="space-y-1.5"
                  :aria-label="t('login.passwordRequirementsAriaLabel')"
                >
                  <li
                    v-for="(requirement, index) in passwordStrength"
                    :key="index"
                    class="flex items-center gap-2"
                    :class="requirement.met ? 'text-success' : 'text-error'"
                  >
                    <UIcon
                      :name="
                        requirement.met
                          ? 'i-lucide-circle-check'
                          : 'i-lucide-circle-x'
                      "
                      class="size-4 shrink-0"
                    />

                    <span class="text-xs/5 font-medium">
                      {{ requirement.text }}
                      <span class="sr-only">
                        {{
                          requirement.met
                            ? t("login.passwordRequirementMet")
                            : t("login.passwordRequirementNotMet")
                        }}
                      </span>
                    </span>
                  </li>
                </ul>
              </div>
            </div>

            <div class="rounded-2xl border border-default/70 bg-muted/30 p-3">
              <UCheckbox v-model="form.remember" :label="t('login.remember')" />
              <p class="pl-6 pt-1 text-xs text-toned">
                {{ t("login.rememberHint") }}
              </p>
            </div>

            <UButton
              :label="t('login.submit')"
              :loading="auth.loading"
              type="submit"
              size="xl"
              class="w-full justify-center"
            />
          </UForm>
        </UPageCard>
      </div>
    </section>
  </div>
</template>
