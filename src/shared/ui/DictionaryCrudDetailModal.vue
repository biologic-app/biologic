<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import type { TabsItem } from "@nuxt/ui";
import type { CrudModuleConfig } from "@/pages/CrudModulePage.vue";
import { apiUpdateRequest, loadReferenceOptions } from "@/shared/api/client.api";
import { formatDateTime } from "@/shared/utils/format";
import { getValueByPath } from "@/shared/utils/object";

type CrudRow = {
  id: string | number;
  [key: string]: unknown;
};

type FieldValue = string | number | boolean | null;

const hiddenReadonlyKeys = new Set(["created_at", "updated_at", "deleted_at"]);

const props = defineProps<{
  open: boolean;
  config: CrudModuleConfig;
  item: CrudRow | null;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "saved", item: CrudRow): void;
}>();

const activeTab = ref<"fields" | "technical" | "notes">("fields");
const editing = ref(false);
const fullscreen = ref(false);
const saving = ref(false);
const note = ref("");
const formState = reactive<Record<string, FieldValue>>({});
const referenceOptions = ref<Record<string, Array<{ label: string; value: FieldValue }>>>({});

const modalUi = computed(() => ({
  content: fullscreen.value
    ? "h-[calc(100vh-1rem)] max-w-[calc(100vw-1rem)] overflow-hidden p-0"
    : "h-[64vh] max-h-[680px] min-h-[30rem] max-w-[calc(100vw-2rem)] overflow-hidden p-0 sm:max-w-4xl",
  header: "p-0",
  body: "p-0",
  footer: "p-0",
}));

const tabs = computed<TabsItem[]>(() => [
  { label: "Поля", icon: "i-lucide-list", value: "fields" },
  { label: "Технический аудит", icon: "i-lucide-history", value: "technical" },
  { label: "Заметки", icon: "i-lucide-message-square", value: "notes" },
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
      label: "Запись",
      description: `Идентификатор: ${row.id}`,
      actor: "system",
      date: row.created_at ?? row.inserted_at ?? null,
    },
    {
      id: "update",
      label: "Последнее сохранение",
      description: "Изменения сохранены через API.",
      actor: "api",
      date: row.updated_at ?? row.modified_at ?? null,
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
  <UModal
    :open="open"
    :ui="modalUi"
    :dismissible="false"
    @update:open="emit('update:open', $event)"
  >
    <template #content>
      <div v-if="item" class="flex h-full flex-col overflow-hidden bg-default">
        <header class="border-b border-default px-5 py-4">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <p class="truncate text-xs font-semibold uppercase tracking-wide text-muted">
                CRUD · {{ config.title }}
              </p>
              <h2 class="mt-1 truncate text-2xl font-semibold text-highlighted">
                {{ title }}
              </h2>
              <p class="mt-1 text-sm text-muted">
                {{ config.description }}
              </p>
            </div>
            <div class="flex shrink-0 items-center gap-1">
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
        </header>

        <UTabs
          v-model="activeTab"
          :items="tabs"
          variant="link"
          :content="false"
          class="border-b border-default px-5"
        />

        <main class="min-h-0 flex-1 overflow-auto px-5 py-5">
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

          <section v-else-if="activeTab === 'technical'" class="max-w-3xl">
            <div class="mb-3 flex items-center justify-between gap-3">
              <h3 class="text-sm font-semibold text-highlighted">
                Технический аудит
              </h3>
              <UBadge color="neutral" variant="outline" :label="`${technicalEvents.length} события`" />
            </div>
            <div class="space-y-4 border-l border-default pl-5">
              <div v-for="event in technicalEvents" :key="event.id" class="relative">
                <span class="absolute -left-[1.82rem] mt-1 size-3 rounded-full border border-default bg-default" />
                <div class="space-y-1">
                  <p class="text-sm font-semibold text-highlighted">
                    {{ event.label }}
                  </p>
                  <p class="text-sm text-muted">
                    {{ event.description }}
                  </p>
                  <p class="font-mono text-xs text-muted">
                    {{ typeof event.date === 'string' ? formatDateTime(event.date) : 'Дата не указана' }}
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section v-else>
            <UTextarea
              v-model="note"
              autoresize
              :rows="4"
              placeholder="Добавьте внутренний комментарий"
            />
          </section>
        </main>

        <footer class="flex justify-end border-t border-default bg-elevated/40 px-5 py-3">
          <UButton
            label="Закрыть"
            color="neutral"
            variant="outline"
            @click="close"
          />
        </footer>
      </div>
    </template>
  </UModal>
</template>
