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
import type { Resource } from "@/shared/types/permissions";

const toast = useToast();
const { t } = useI18n();
const auth = useAuth();

const open = ref(false);

const canViewDashboard = computed(() => auth.can("dashboard", "view"));
const canViewResearch = computed(() => auth.can("research", "view"));
const canViewDirections = computed(() => auth.can("directions", "view"));
const canViewSamples = computed(() => auth.can("samples", "view"));
const canViewTests = computed(() => auth.can("tests", "view"));
const canViewDictionaries = computed(() =>
  dictionaryItems.some((item) => auth.can(item.key as Resource, "view")),
);
const canViewAccess = computed(
  () => auth.can("users", "view") || auth.can("user-types", "view"),
);

const accessKeyToResource: Record<string, Resource> = {
  users: "users",
  roles: "user-types",
};

const links = computed<NavigationMenuItem[][]>(() => [
  [
    {
      label: t("nav.home"),
      icon: canViewDashboard.value ? "i-lucide-layout-dashboard" : "i-lucide-lock",
      to: { name: "dashboard" },
      disabled: !canViewDashboard.value,
      onSelect: () => {
        open.value = false;
      },
    },
    {
      label: t("nav.research"),
      icon: canViewResearch.value ? "i-lucide-flask-conical" : "i-lucide-lock",
      to: { name: "research" },
      disabled: !canViewResearch.value,
      onSelect: () => {
        open.value = false;
      },
    },
    {
      label: t("nav.directions"),
      icon: canViewDirections.value ? "i-lucide-book-copy" : "i-lucide-lock",
      to: { name: "directions" },
      disabled: !canViewDirections.value,
      type: "trigger",
      defaultOpen: false,
    },
    {
      label: t("nav.samples"),
      icon: canViewSamples.value ? "i-lucide-test-tube-2" : "i-lucide-lock",
      to: { name: "samples" },
      disabled: !canViewSamples.value,
      onSelect: () => {
        open.value = false;
      },
    },
    {
      label: t("nav.tests"),
      icon: canViewTests.value ? "i-lucide-clipboard-list" : "i-lucide-lock",
      to: { name: "tests" },
      disabled: !canViewTests.value,
      onSelect: () => {
        open.value = false;
      },
    },
    {
      label: t("nav.dictionaries"),
      icon: canViewDictionaries.value ? "i-lucide-library" : "i-lucide-lock",
      to: { name: "dictionaries" },
      disabled: !canViewDictionaries.value,
      type: "trigger",
      defaultOpen: false,
      children: dictionaryItems.map((item) => {
        const canView = auth.can(item.key as Resource, "view");
        return {
          label: item.label,
          icon: canView ? item.icon : "i-lucide-lock",
          disabled: !canView,
          to:
            item.key === "statuses"
              ? "/dictionaries/statuses"
              : `/dictionaries/${item.key}`,
          onSelect: () => {
            open.value = false;
          },
        };
      }),
    },
    {
      label: t("nav.access"),
      icon: canViewAccess.value ? "i-lucide-shield-check" : "i-lucide-lock",
      to: { name: "access-users" },
      disabled: !canViewAccess.value,
      type: "trigger",
      defaultOpen: false,
      children: accessItems.map((item) => {
        const resource = accessKeyToResource[item.key] ?? (item.key as Resource);
        const canView = auth.can(resource, "view");
        return {
          label: item.label,
          icon: canView ? item.icon : "i-lucide-lock",
          disabled: !canView,
          to: item.to,
          onSelect: () => {
            open.value = false;
          },
        };
      }),
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
