<script setup lang="ts">
import { computed } from "vue";
import type { DropdownMenuItem } from "@nuxt/ui";
import { useColorMode } from "@vueuse/core";
import { useI18n } from "vue-i18n";
import { useLocale } from "@/shared/composables/useLocale";
import { useAppearanceSettings } from "@/shared/composables/useAppearanceSettings";
import { useAuth } from "@/modules/auth";
import { userModeList } from "@/shared/config/user-modes";

defineProps<{
  collapsed?: boolean;
}>();

const colorMode = useColorMode();
const appConfig = useAppConfig();
const toast = useToast();
const { t } = useI18n();
const { locale } = useLocale();
const {
  font,
  fontSize,
  fontOptions,
  fontSizeOptions,
} = useAppearanceSettings();
const auth = useAuth();

const colors = [
  "red",
  "orange",
  "amber",
  "yellow",
  "lime",
  "green",
  "emerald",
  "teal",
  "cyan",
  "sky",
  "blue",
  "indigo",
  "violet",
  "purple",
  "fuchsia",
  "pink",
  "rose",
];
const neutrals = ["slate", "gray", "zinc", "neutral", "stone"];

const user = computed(() => {
  const name = auth.user?.fullName || auth.user?.login;

  return {
    name: name || "User",
    // No external avatar source: UAvatar falls back to initials derived
    // from `alt` (or a generic icon when no name is known), so the fully
    // offline deployment never requests an image from the network.
    avatar: name
      ? { alt: name }
      : { icon: "i-lucide-user" },
  };
});

const items = computed<DropdownMenuItem[][]>(() => [
  [
    {
      type: "label",
      label: user.value.name,
      avatar: user.value.avatar,
    },
  ],
  [
    {
      label: t("userMenu.palette"),
      icon: "i-lucide-palette",
      children: [
        {
          label: t("userMenu.primary"),
          slot: "chip",
          chip: appConfig.ui.colors.primary,
          content: {
            align: "center",
            collisionPadding: 16,
          },
          children: colors.map((color) => ({
            label: color,
            chip: color,
            slot: "chip",
            checked: appConfig.ui.colors.primary === color,
            type: "checkbox",
            onSelect: (e) => {
              e.preventDefault();
              appConfig.ui.colors.primary = color;
            },
          })),
        },
        {
          label: t("userMenu.neutral"),
          slot: "chip",
          chip:
            appConfig.ui.colors.neutral === "neutral"
              ? "old-neutral"
              : appConfig.ui.colors.neutral,
          content: {
            align: "end",
            collisionPadding: 16,
          },
          children: neutrals.map((color) => ({
            label: color,
            chip: color === "neutral" ? "old-neutral" : color,
            slot: "chip",
            type: "checkbox",
            checked: appConfig.ui.colors.neutral === color,
            onSelect: (e) => {
              e.preventDefault();
              appConfig.ui.colors.neutral = color;
            },
          })),
        },
      ],
    },
    {
      label: t("userMenu.theme"),
      icon: "i-lucide-sun-moon",
      children: [
        {
          label: t("userMenu.light"),
          icon: "i-lucide-sun",
          type: "checkbox",
          checked: colorMode.value === "light",
          onSelect(e: Event) {
            e.preventDefault();
            colorMode.value = "light";
          },
        },
        {
          label: t("userMenu.dark"),
          icon: "i-lucide-moon",
          type: "checkbox",
          checked: colorMode.value === "dark",
          onUpdateChecked(checked: boolean) {
            if (checked) {
              colorMode.value = "dark";
            }
          },
          onSelect(e: Event) {
            e.preventDefault();
          },
        },
      ],
    },
    {
      label: t("app.language"),
      icon: "i-lucide-languages",
      children: [
        {
          label: t("app.russian"),
          type: "checkbox",
          checked: locale.value === "ru",
          onSelect(e: Event) {
            e.preventDefault();
            locale.value = "ru";
          },
        },
        {
          label: t("app.english"),
          type: "checkbox",
          checked: locale.value === "en",
          onSelect(e: Event) {
            e.preventDefault();
            locale.value = "en";
          },
        },
      ],
    },
    {
      label: t("userMenu.font"),
      icon: "i-lucide-type",
      children: fontOptions.map((option) => ({
        label: option.label,
        type: "checkbox",
        checked: font.value === option.value,
        onSelect(e: Event) {
          e.preventDefault();
          font.value = option.value;
        },
      })),
    },
    {
      label: t("userMenu.fontSize"),
      icon: "i-lucide-text-cursor-input",
      children: fontSizeOptions.map((option) => ({
        label: option.label,
        type: "checkbox",
        checked: fontSize.value === option.value,
        onSelect(e: Event) {
          e.preventDefault();
          fontSize.value = option.value;
        },
      })),
    },
    {
      label: t("userMenu.mode"),
      icon: "i-lucide-user-cog",
      children: userModeList.map((mode) => ({
        label: t(mode.labelKey),
        icon: mode.icon,
        type: "checkbox",
        checked: auth.activeModeId === mode.id,
        async onSelect(e: Event) {
          e.preventDefault();
          try {
            await auth.loginAs(mode.id);
            toast.add({
              title: t("modes.changed"),
              description: t("modes.changedTo", { mode: t(mode.labelKey) }),
              color: "success",
            });
          } catch {
            toast.add({
              title: t("login.errorTitle"),
              description: t("login.errorDescription"),
              color: "error",
            });
          }
        },
      })),
    },
  ],
  [
    {
      label: t("userMenu.logout"),
      icon: "i-lucide-log-out",
      onSelect: async () => {
        await auth.logout();
        toast.add({
          title: t("userMenu.logoutTitle"),
          description: t("userMenu.logoutDescription"),
          color: "success",
        });
      },
    },
  ],
]);
</script>

<template>
  <UDropdownMenu
    :items="items"
    :content="{ align: 'center', collisionPadding: 12 }"
    :ui="{
      content: collapsed ? 'w-48' : 'w-(--reka-dropdown-menu-trigger-width)',
    }"
  >
    <UButton
      v-bind="{
        ...user,
        label: collapsed ? undefined : user?.name,
        trailingIcon: collapsed ? undefined : 'i-lucide-chevrons-up-down',
      }"
      color="neutral"
      variant="ghost"
      block
      :square="collapsed"
      class="data-[state=open]:bg-elevated"
      :ui="{
        trailingIcon: 'text-dimmed',
      }"
    />

    <template #chip-leading="{ item }">
      <div class="inline-flex items-center justify-center shrink-0 size-5">
        <span
          class="rounded-full ring ring-bg bg-(--chip-light) dark:bg-(--chip-dark) size-2"
          :style="{
            '--chip-light': `var(--color-${(item as any).chip}-500)`,
            '--chip-dark': `var(--color-${(item as any).chip}-400)`,
          }"
        />
      </div>
    </template>
  </UDropdownMenu>
</template>
