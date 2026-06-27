<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import type { TabsItem } from "@nuxt/ui";
import type { CrudModuleConfig, CrudRow } from '@/shared/types/crud';
import { apiUpdateRequest, loadReferenceOptions } from "@/shared/api/client.api";
import EntityDetailModalShell, { type DetailListItem } from "@/shared/ui/EntityDetailModalShell.vue";
import TechnicalAuditTimeline from "@/shared/ui/TechnicalAuditTimeline.vue";
import { formatDateTime } from "@/shared/utils/format";
import { getValueByPath } from "@/shared/utils/object";

type FieldValue = string | number | boolean | null;

const hiddenReadonlyKeys = new Set(["created_at", "updated_at", "deleted_at"]);

const props = defineProps<{
  open: boolean;
  config: CrudModuleConfig;
  item: CrudRow | null;
  listItems?: DetailListItem[];
  listHasMore?: boolean;
  listLoadingMore?: boolean;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "saved", item: CrudRow): void;
  (event: "select", id: string | number): void;
  (event: "list-load-more"): void;
}>();

const activeTab = ref("fields");
const editing = ref(false);
const saving = ref(false);
const formState = reactive<Record<string, FieldValue>>({});
const referenceOptions = ref<Record<string, Array<{ label: string; value: FieldValue }>>>({});

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

const visibleFields = computed(() => {
  const item = props.item;
  if (!item) return [];

  const configuredFields = props.config.fields.map((field) => ({
    ...field,
    editable: true,
    value: getValueByPath(item, field.key),
  }));

  const configuredKeys = new Set(configuredFields.map((field) => field.key));
  const readonlyFields = Object.entries(item)
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

  return [
    {
      id: "entity",
      label: "Запись создана",
      description: `Код записи: ${entityDisplayCode(row.id)}`,
      actor: "system",
      date: auditDate(row.created_at ?? row.inserted_at),
    },
    {
      id: "update",
      label: "Последнее сохранение",
      description: "Изменения сохранены через API.",
      actor: "api",
      date: auditDate(row.updated_at ?? row.modified_at),
    },
    {
      id: "status",
      label: "Текущее состояние",
      description: currentStateLabel(row),
      actor: "process",
      date: auditDate(row.updated_at ?? row.modified_at ?? row.created_at ?? row.inserted_at),
    },
  ];
});

watch(
  () => [props.open, props.item?.id] as const,
  async ([open]) => {
    if (!open) {
      editing.value = false;
      return;
    }

    activeTab.value = "fields";
    syncForm();
    await loadSelectOptions();
  },
  { immediate: true },
);

function syncForm() {
  props.config.fields.forEach((field) => {
    formState[field.key] = normalizeFormValue(props.item ? getValueByPath(props.item, field.key) : null);
  });
}

async function loadSelectOptions() {
  await Promise.all(
    props.config.fields
      .filter((field) => field.type === "select" && field.source && !referenceOptions.value[field.key])
      .map(async (field) => {
        const options = await loadReferenceOptions(field.source as string).catch(() => []);
        referenceOptions.value = {
          ...referenceOptions.value,
          [field.key]: options as Array<{ label: string; value: FieldValue }>,
        };
      }),
  );
}

async function saveInline() {
  if (!props.item) return;

  saving.value = true;
  try {
    const payload = Object.fromEntries(
      props.config.fields.map((field) => [field.key, formState[field.key] ?? null]),
    );
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

function normalizeFormValue(value: unknown): FieldValue {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }

  if (value === null || value === undefined) {
    return null;
  }

  return String(value);
}

function formString(key: string) {
  const value = formState[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function formBoolean(key: string) {
  return Boolean(formState[key]);
}

function setFormValue(key: string, value: unknown) {
  formState[key] = normalizeFormValue(value);
}

function isEditableField(field: { key: string; editable?: boolean }) {
  return Boolean(field.editable && configuredFieldMap.value.has(field.key));
}

function formatPlain(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatDisplay(value: unknown): string {
  if (typeof value === "string" && /(T|\d{4}-\d{2}-\d{2})/.test(value)) {
    return formatDateTime(value);
  }

  return formatPlain(value);
}

function pickText(row: CrudRow, paths: string[]) {
  for (const path of paths) {
    const text = formatPlain(getValueByPath(row, path));
    if (text !== "-") return text;
  }

  return "";
}

function entityDisplayCode(value: unknown) {
  if (typeof value !== "string" && typeof value !== "number") {
    return "-";
  }

  const text = String(value);
  const uuidPrefix = text.match(/^[0-9a-f]{8}/i)?.[0];
  return `#${(uuidPrefix ?? text).toUpperCase()}`;
}

function auditDate(value: unknown) {
  return typeof value === "string" ? value : null;
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

function inferFieldType(value: unknown) {
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
    @update:open="emit('update:open', $event)"
    @select="emit('select', $event)"
    @list-load-more="emit('list-load-more')"
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
              @click="editing = false; syncForm()"
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

      <div class="overflow-hidden rounded-lg border border-default">
        <dl class="grid text-sm md:grid-cols-2">
          <div
            v-for="field in visibleFields"
            :key="field.key"
            class="grid grid-cols-[9.5rem_minmax(0,1fr)] border-b border-default last:border-b-0 md:[&:nth-last-child(-n+2)]:border-b-0 md:odd:border-e"
          >
            <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
              {{ field.label }}
            </dt>
            <dd class="min-w-0 px-3 py-2 text-muted">
              <template v-if="editing && isEditableField(field)">
                <UTextarea
                  v-if="field.type === 'textarea'"
                  :model-value="formString(field.key)"
                  autoresize
                  :rows="2"
                  @update:model-value="setFormValue(field.key, $event)"
                />
                <USwitch
                  v-else-if="field.type === 'boolean'"
                  :model-value="formBoolean(field.key)"
                  @update:model-value="setFormValue(field.key, $event)"
                />
                <USelectMenu
                  v-else-if="field.type === 'select'"
                  v-model="formState[field.key]"
                  :items="referenceOptions[field.key] || []"
                  value-key="value"
                  label-key="label"
                  class="w-full"
                />
                <UInput
                  v-else
                  :model-value="formString(field.key)"
                  :type="field.type === 'number' ? 'number' : 'text'"
                  @update:model-value="setFormValue(field.key, $event)"
                />
              </template>
              <span v-else class="block truncate">
                {{ formatDisplay(field.value) }}
              </span>
            </dd>
          </div>
        </dl>
      </div>
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
