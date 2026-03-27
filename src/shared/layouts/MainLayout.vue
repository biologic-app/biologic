<script setup lang="ts">
import { computed, ref } from "vue";
import { useStorage } from "@vueuse/core";
import type { NavigationMenuItem } from "@nuxt/ui";
import { useI18n } from "vue-i18n";
import NotificationsSlideover from "@/shared/components/NotificationsSlideover.vue";
import UserMenu from "@/shared/components/UserMenu.vue";
import { useAuthStore } from "@/modules/auth";
import { useRouter } from "vue-router";

const toast = useToast();
const { t } = useI18n();
const auth = useAuthStore();
const router = useRouter();

const open = ref(false);
const unreadNotifications = ref(4);

const links = computed<NavigationMenuItem[][]>(() => [
  [
    {
      label: t("nav.home"),
      icon: "i-lucide-layout-dashboard",
      to: { name: "dashboard" },
      onSelect: () => {
        open.value = false;
      },
    },
    {
      label: t("nav.inbox"),
      icon: "i-lucide-inbox",
      to: { name: "inbox" },
      badge: unreadNotifications.value,
      onSelect: () => {
        open.value = false;
      },
    },
    {
      label: t("nav.customers"),
      icon: "i-lucide-users",
      to: { name: "customers" },
      onSelect: () => {
        open.value = false;
      },
    },
    {
      label: t("nav.directions"),
      icon: "i-lucide-book-copy",
      to: { name: "directions" },
      type: "trigger",
      defaultOpen: false,
    },
    {
      label: t("nav.settings"),
      icon: "i-lucide-settings",
      to: { name: "settings" },
      type: "trigger",
      defaultOpen: false,
      children: [
        {
          label: t("settings.general"),
          to: { name: "settings" },
          onSelect: () => {
            open.value = false;
          },
        },
        {
          label: t("settings.members"),
          to: { name: "settings-members" },
          onSelect: () => {
            open.value = false;
          },
        },
        {
          label: t("settings.notifications"),
          to: { name: "settings-notifications" },
          onSelect: () => {
            open.value = false;
          },
        },
        {
          label: t("settings.security"),
          to: { name: "settings-security" },
          onSelect: () => {
            open.value = false;
          },
        },
      ],
    },
  ],
  [
    {
      label: t("nav.documentation"),
      icon: "i-lucide-book-open",
      to: "https://github.com/nuxt-ui-templates/dashboard-vue",
      target: "_blank",
    },
  ],
  [
    {
      label: t("userMenu.logout"),
      color: "error",
      icon: "i-lucide-log-out",
      onSelect: async () => {
        await auth.logout();
        await router.push({ name: "login" });
        toast.add({
          title: t("userMenu.logoutTitle"),
          description: t("userMenu.logoutDescription"),
          color: "success",
        });
      },
    },
  ],
]);

const groups = computed(() => [
  {
    id: "links",
    label: t("layout.goTo"),
    items: links.value.flat() as undefined[],
  },
  {
    id: "quick-actions",
    label: t("layout.quickActions"),
    items: [
      {
        label: t("layout.createOrder"),
        icon: "i-lucide-plus",
        to: "/orders/new",
      },
      {
        label: t("layout.importData"),
        icon: "i-lucide-plus",
        to: "/import",
      },
      {
        label: t("layout.exportData"),
        icon: "i-lucide-plus",
        to: "/export",
      },
    ],
  },
]);

const cookie = useStorage("cookie-consent", "pending");
if (cookie.value !== "accepted") {
  toast.add({
    title: t("layout.cookieTitle"),
    duration: 0,
    close: false,
    actions: [
      {
        label: t("layout.accept"),
        color: "neutral",
        variant: "outline",
        onClick: () => {
          cookie.value = "accepted";
        },
      },
      {
        label: t("layout.decline"),
        color: "neutral",
        variant: "ghost",
      },
    ],
  });
}
</script>

<template>
  <UDashboardGroup unit="rem" storage="local">
    <UDashboardSidebar
      id="default"
      v-model:open="open"
      collapsible
      resizable
      :ui="{
        header: 'lg:border-b lg:border-default',
        footer: 'lg:border-t lg:border-default',
      }"
    >
      <template #header="{ collapsed }">
        <UserMenu :collapsed="collapsed" />
      </template>

      <template #default="{ collapsed }">
        <UDashboardSearchButton
          :collapsed="collapsed"
          class="bg-transparent ring-default"
        />

        <UNavigationMenu
          :collapsed="collapsed"
          :items="links[0]"
          orientation="vertical"
          tooltip
          popover
        />

        <UNavigationMenu
          :collapsed="collapsed"
          :items="links[1]"
          orientation="vertical"
          tooltip
          class="mt-auto"
        />
      </template>
      <template #footer="{ collapsed }">
        <UNavigationMenu
          :collapsed="collapsed"
          :items="links[2]"
          orientation="vertical"
          tooltip
          popover
        />
      </template>
    </UDashboardSidebar>

    <UDashboardSearch :groups="groups" />

    <RouterView />

    <NotificationsSlideover />
  </UDashboardGroup>
</template>
