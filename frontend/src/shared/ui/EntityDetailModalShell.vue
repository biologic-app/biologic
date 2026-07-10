<script setup lang="ts">
import { computed, ref } from "vue";
import type { TabsItem } from "@nuxt/ui";
import EntityDetailBreadcrumb from "@/shared/ui/EntityDetailBreadcrumb.vue";
import EntityDetailMasterList, {
  type DetailListItem,
} from "@/shared/ui/EntityDetailMasterList.vue";

export type { DetailListItem, DetailListColor } from "@/shared/ui/EntityDetailMasterList.vue";

// Единый каркас всех детальных модалок (справочники, доступ, бизнес-сущности):
// UModal + fullscreen + опциональный левый master-список + шапка (крошки/eyebrow,
// действия, заголовок) + строка вкладок + тело + футер. Доменная разметка приходит
// слотами: #header (второй ряд шапки), #header-actions (кнопки справа), #tabs-trailing
// (иконка справа от вкладок), default (тело), #footer.
const props = withDefaults(
  defineProps<{
    open: boolean;
    eyebrow?: string;
    title?: string;
    subtitle?: string;
    tabs: TabsItem[];
    size?: "md" | "lg" | "xl";
    defaultFullscreen?: boolean;
    ready?: boolean;
    listItems?: DetailListItem[];
    listLabel?: string;
    selectedId?: string | number | null;
    listHasMore?: boolean;
    listLoadingMore?: boolean;
    breadcrumbs?: Array<{ label: string }>;
    bodyClass?: string;
  }>(),
  {
    eyebrow: "",
    title: "",
    subtitle: undefined,
    size: "md",
    defaultFullscreen: false,
    ready: true,
    listItems: undefined,
    listLabel: "",
    selectedId: null,
    listHasMore: false,
    listLoadingMore: false,
    breadcrumbs: () => [],
    bodyClass: undefined,
  },
);

const activeTab = defineModel<string>("activeTab", { required: true });

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "select", id: string | number): void;
  (event: "list-load-more"): void;
  (event: "go-to-level", index: number): void;
}>();

const fullscreen = ref(props.defaultFullscreen);
const hasList = computed(() => Array.isArray(props.listItems));

const SIZE_CLASS = {
  md: "h-[64vh] max-h-[680px] min-h-[30rem] max-w-[calc(100vw-2rem)] overflow-hidden p-0 sm:max-w-4xl",
  lg: "h-[78vh] max-h-[820px] min-h-[38rem] max-w-[calc(100vw-2rem)] overflow-hidden p-0 sm:max-w-6xl",
  xl: "h-[82vh] max-h-[860px] min-h-[42rem] max-w-[calc(100vw-2rem)] overflow-hidden p-0 sm:max-w-7xl",
} as const;

const modalUi = computed(() => {
  const base = fullscreen.value
    ? "h-[calc(100vh-1rem)] max-w-[calc(100vw-1rem)] overflow-hidden p-0"
    : SIZE_CLASS[props.size];
  const widened = hasList.value && !fullscreen.value
    ? base.replace("sm:max-w-4xl", "sm:max-w-6xl").replace("sm:max-w-6xl", "sm:max-w-7xl")
    : base;

  return { content: widened, header: "p-0", body: "p-0", footer: "p-0" };
});

function close() {
  emit("update:open", false);
}
</script>

<template>
  <UModal
    :open="open"
    :ui="modalUi"
    :dismissible="false"
    @update:open="emit('update:open', $event)"
  >
    <template #content>
      <div v-if="ready" class="flex h-full overflow-hidden bg-default">
        <EntityDetailMasterList
          v-if="hasList"
          :items="listItems ?? []"
          :label="listLabel"
          :selected-id="selectedId"
          :has-more="listHasMore"
          :loading-more="listLoadingMore"
          @select="emit('select', $event)"
          @load-more="emit('list-load-more')"
        />

        <div class="flex h-full min-w-0 flex-1 flex-col overflow-hidden">
          <header class="border-b border-default px-5 py-4">
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0 flex-1">
                <EntityDetailBreadcrumb
                  v-if="breadcrumbs.length"
                  :items="breadcrumbs"
                  @go-to-level="emit('go-to-level', $event)"
                />
                <p
                  v-else
                  class="truncate text-xs font-semibold uppercase tracking-wide text-muted"
                >
                  {{ eyebrow }}
                </p>
                <template v-if="!$slots.header">
                  <h2 class="mt-1 truncate text-2xl font-semibold text-highlighted">
                    {{ title }}
                  </h2>
                  <p v-if="subtitle" class="mt-1 text-sm text-muted">
                    {{ subtitle }}
                  </p>
                </template>
              </div>
              <div class="flex shrink-0 items-center gap-1">
                <slot name="header-actions" />
                <UTooltip :text="fullscreen ? 'Обычный размер' : 'На весь экран'">
                  <UButton
                    :icon="fullscreen ? 'i-lucide-minimize-2' : 'i-lucide-maximize-2'"
                    color="neutral"
                    variant="ghost"
                    square
                    @click="fullscreen = !fullscreen"
                  />
                </UTooltip>
                <UButton
                  icon="i-lucide-x"
                  color="neutral"
                  variant="ghost"
                  square
                  @click="close"
                />
              </div>
            </div>

            <slot name="header" />
          </header>

          <div class="flex items-center border-b border-default px-5">
            <UTabs
              v-model="activeTab"
              :items="tabs"
              variant="link"
              :content="false"
            />
            <slot name="tabs-trailing" />
          </div>

          <main class="min-h-0 flex-1 px-5 py-5" :class="bodyClass ?? 'overflow-auto'">
            <slot />
          </main>

          <footer
            v-if="$slots.footer"
            class="flex justify-end gap-2 border-t border-default bg-elevated/40 px-5 py-3"
          >
            <slot name="footer" :close="close" />
          </footer>
        </div>
      </div>
    </template>
  </UModal>
</template>
