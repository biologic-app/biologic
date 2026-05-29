<script setup lang="ts">
import { computed, ref } from "vue";
import { useStorage } from "@vueuse/core";
import type {
  CommandPaletteGroup,
  CommandPaletteItem,
  NavigationMenuItem,
} from "@nuxt/ui";
import { useI18n } from "vue-i18n";
import NotificationsSlideover from "@/shared/ui/NotificationsSlideover.vue";
import UserMenu from "@/shared/ui/UserMenu.vue";
import { useAuth } from "@/modules/auth";
import { dictionaryItems } from "@/modules/dictionaries/config";
import { accessItems } from "@/modules/access/config";

const toast = useToast();
const { t } = useI18n();
const auth = useAuth();

const open = ref(false);

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
      label: t("nav.research"),
      icon: "i-lucide-flask-conical",
      to: { name: "research" },
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
      label: t("nav.samples"),
      icon: "i-lucide-test-tube-2",
      to: { name: "samples" },
      onSelect: () => {
        open.value = false;
      },
    },
    {
      label: t("nav.dictionaries"),
      icon: "i-lucide-library",
      to: { name: "dictionaries" },
      type: "trigger",
      defaultOpen: false,
      children: dictionaryItems.map((item) => ({
        label: item.label,
        icon: item.icon,
        to:
          item.key === "statuses"
            ? "/dictionaries/statuses"
            : `/dictionaries/${item.key}`,
        onSelect: () => {
          open.value = false;
        },
      })),
    },
    {
      label: t("nav.access"),
      icon: "i-lucide-shield-check",
      to: { name: "access-users" },
      type: "trigger",
      defaultOpen: false,
      children: accessItems.map((item) => ({
        label: item.label,
        icon: item.icon,
        to: item.to,
        onSelect: () => {
          open.value = false;
        },
      })),
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
        toast.add({
          title: t("userMenu.logoutTitle"),
          description: t("userMenu.logoutDescription"),
          color: "success",
        });
      },
    },
  ],
]);

const groups = computed<CommandPaletteGroup<CommandPaletteItem>[]>(() => [
  {
    id: "links",
    label: t("layout.goTo"),
    items: links.value.flat() as CommandPaletteItem[],
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
