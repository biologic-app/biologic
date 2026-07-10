<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { TabsItem } from "@nuxt/ui";
import type { CrudModuleConfig, CrudRow } from '@/shared/types/crud';
import { apiUpdateRequest, loadReferenceOptions } from "@/shared/api/client.api";
import { useEntityForm } from "@/shared/composables/useEntityForm";
import EntityDetailModalShell, { type DetailListItem } from "@/shared/ui/EntityDetailModalShell.vue";
import EntityFieldGrid, { type FieldOption, type GridField } from "@/shared/ui/EntityFieldGrid.vue";
import TechnicalAuditTimeline from "@/shared/ui/TechnicalAuditTimeline.vue";
import { buildFallbackAuditEvents } from "@/shared/ui/entity-technical-audit";
import { pickText } from "@/shared/ui/entity-detail.helpers";
import { getValueByPath } from "@/shared/utils/object";

const hiddenReadonlyKeys = new Set(["created_at", "updated_at", "deleted_at"]);

const props = defineProps<{
  open: boolean;
  config: CrudModuleConfig;
  item: CrudRow | null;
  listItems?: DetailListItem[];
  listHasMore?: boolean;
  listLoadingMore?: boolean;
  breadcrumbs?: Array<{ label: string }>;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "saved", item: CrudRow): void;
  (event: "select", id: string | number): void;
  (event: "list-load-more"): void;
  (event: "go-to-level", index: number): void;
}>();

const activeTab = ref("fields");
const editing = ref(false);
const saving = ref(false);
const { formState, sync, setValue, buildPayload } = useEntityForm();
const referenceOptions = ref<Record<string, FieldOption[]>>({});

const tabs = computed<TabsItem[]>(() => [
  { label: "Поля", icon: "i-lucide-list", value: "fields" },
  { label: "Технический аудит", icon: "i-lucide-history", value: "technical" },
]);

const title = computed(() => {
  if (!props.item) return props.config.title;
  return pickText(props.item, ["name", "full_name", "code", "key"]) || `${props.config.title} #${props.item.id}`;
});

const configuredFieldMap = computed(() =>
  new Map(props.config.fields.map((field) => [field.key, field])),
);

const visibleFields = computed<GridField[]>(() => {
  const item = props.item;
  if (!item) return [];

  const configuredFields: GridField[] = props.config.fields.map((field) => ({
    key: field.key,
    label: field.label,
    type: field.type === "file" ? "text" : field.type,
    required: field.required,
    options: field.options,
    editable: true,
    value: getValueByPath(item, field.key),
  }));

  const configuredKeys = new Set(configuredFields.map((field) => field.key));
  const readonlyFields: GridField[] = Object.entries(item)
    .filter(([key]) => !configuredKeys.has(key) && !hiddenReadonlyKeys.has(key))
    .map(([key, value]) => ({
      key,
      label: labelForKey(key),
      type: inferFieldType(value),
      editable: false,
      value,
    }));

  return [...configuredFields, ...readonlyFields];
});

const technicalEvents = computed(() => {
  const row = props.item;
  if (!row) return [];

  return buildFallbackAuditEvents(row, {
    stateLabel: currentStateLabel(row),
    savedDescription: "Изменения сохранены через API.",
  });
});

watch(
  () => [props.open, props.item?.id] as const,
  async ([open]) => {
    if (!open) {
      editing.value = false;
      return;
    }

    activeTab.value = "fields";
    sync(props.config.fields, props.item);
    await loadSelectOptions();
  },
  { immediate: true },
);

async function loadSelectOptions() {
  await Promise.all(
    props.config.fields
      .filter((field) => field.type === "select" && field.source && !referenceOptions.value[field.key])
      .map(async (field) => {
        const options = await loadReferenceOptions(field.source as string).catch(() => []);
        referenceOptions.value = {
          ...referenceOptions.value,
          [field.key]: options as FieldOption[],
        };
      }),
  );
}

async function saveInline() {
  if (!props.item) return;

  saving.value = true;
  try {
    const payload = buildPayload(props.config.fields);
    const response = await apiUpdateRequest<CrudRow>(`${props.config.endpoint}/${props.item.id}`, {
      method: "PATCH",
      body: payload,
    });
    const next = { ...props.item, ...payload, ...response.data };
    editing.value = false;
    emit("saved", next);
  } finally {
    saving.value = false;
  }
}

function close() {
  emit("update:open", false);
}

function isEditableField(field: GridField) {
  return Boolean(field.editable && configuredFieldMap.value.has(field.key));
}

function currentStateLabel(row: CrudRow) {
  const status = pickText(row, ["status.name", "state.name", "status", "state"]);
  if (status) return status;

  if (typeof row.is_active === "boolean") {
    return row.is_active ? "Активна" : "Неактивна";
  }

  if (row.deleted_at) {
    return "Удалена";
  }

  return "Актуальная запись";
}

function labelForKey(key: string) {
  const labels: Record<string, string> = {
    id: "ID",
    created_at: "Создано",
    updated_at: "Обновлено",
  };

  if (labels[key]) return labels[key];

  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function inferFieldType(value: unknown): GridField["type"] {
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return "number";
  if (typeof value === "string" && value.length > 80) return "textarea";
  return "text";
}
</script>

<template>
  <EntityDetailModalShell
    v-model:active-tab="activeTab"
    :open="open"
    :eyebrow="`CRUD · ${config.title}`"
    :title="title"
    :subtitle="config.description"
    :tabs="tabs"
    size="md"
    :list-items="listItems"
    :selected-id="item?.id ?? null"
    :list-has-more="listHasMore"
    :list-loading-more="listLoadingMore"
    :breadcrumbs="breadcrumbs"
    @update:open="emit('update:open', $event)"
    @select="emit('select', $event)"
    @list-load-more="emit('list-load-more')"
    @go-to-level="emit('go-to-level', $event)"
  >
    <section v-if="activeTab === 'fields'" class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <h3 class="text-sm font-semibold text-highlighted">
          Поля записи
        </h3>
        <div class="flex gap-2">
          <UButton
            v-if="!editing"
            label="Редактировать"
            icon="i-lucide-pencil"
            color="neutral"
            variant="outline"
            size="sm"
            @click="editing = true"
          />
          <template v-else>
            <UButton
              label="Отменить"
              color="neutral"
              variant="outline"
              size="sm"
              :disabled="saving"
              @click="editing = false; sync(config.fields, item)"
            />
            <UButton
              label="Сохранить"
              icon="i-lucide-save"
              size="sm"
              :loading="saving"
              @click="saveInline"
            />
          </template>
        </div>
      </div>

      <EntityFieldGrid
        :fields="visibleFields"
        :editing="editing"
        :form-state="formState"
        :reference-options="referenceOptions"
        :is-editable="isEditableField"
        @update="setValue"
      />
    </section>

    <TechnicalAuditTimeline
      v-else
      :events="technicalEvents"
    />

    <template #footer>
      <UButton
        label="Закрыть"
        color="neutral"
        variant="outline"
        @click="close"
      />
    </template>
  </EntityDetailModalShell>
</template>
