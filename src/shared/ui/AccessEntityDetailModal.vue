<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import type { TabsItem } from "@nuxt/ui";
import PermissionEditor from "@/shared/ui/PermissionEditor.vue";
import type { Permission, PermissionOverride } from "@/shared/types/permissions";
import { formatDateTime } from "@/shared/utils/format";

type AccessKind = "user" | "role";

type AccessRow = {
  id: string | number;
  [key: string]: unknown;
};

type AccessMode = "view" | "edit" | "create";

type FieldOption = {
  label: string;
  value: string | number | boolean | null;
};

type DetailField = {
  key: string;
  label: string;
  type?: "text" | "password" | "boolean" | "select";
  required?: boolean;
};

const props = defineProps<{
  open: boolean;
  title: string;
  kind: AccessKind;
  mode: AccessMode;
  item: AccessRow | null;
  loading?: boolean;
  saving?: boolean;
  readOnly?: boolean;
  editable?: boolean;
  permissions?: Permission[];
  rolePermissions?: Permission[];
  overrides?: PermissionOverride[];
  fieldOptions?: Record<string, FieldOption[]>;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "save", payload: Record<string, unknown>): void;
  (event: "edit"): void;
  (event: "update:permissions", value: Permission[]): void;
  (event: "update:overrides", value: PermissionOverride[]): void;
}>();

const activeTab = ref<"fields" | "technical" | "permissions">("fields");
const fullscreen = ref(false);
const formRef = ref<HTMLFormElement | null>(null);
const form = reactive<Record<string, unknown>>({});

const modalUi = computed(() => ({
  content: fullscreen.value
    ? "h-[calc(100vh-1rem)] max-w-[calc(100vw-1rem)] overflow-hidden p-0"
    : "h-[78vh] max-h-[820px] min-h-[38rem] max-w-[calc(100vw-2rem)] overflow-hidden p-0 sm:max-w-6xl",
  header: "p-0",
  body: "p-0",
  footer: "p-0",
}));

const tabs = computed<TabsItem[]>(() => {
  return [
    { label: "Поля", icon: "i-lucide-list", value: "fields" },
    { label: "Технический аудит", icon: "i-lucide-history", value: "technical" },
    {
      label: props.kind === "user" ? "Права и роли" : "Права роли",
      icon: "i-lucide-shield-check",
      value: "permissions",
    },
  ];
});

const detailFields = computed<DetailField[]>(() => {
  if (props.kind === "role") {
    return [
      { key: "key", label: "Ключ", required: true },
      { key: "name", label: "Название", required: true },
      { key: "scope_type", label: "Область роли", type: "select", required: true },
    ];
  }

  const userFields: DetailField[] = [
    { key: "username", label: "Логин", required: true },
    { key: "code", label: "Код" },
    { key: "first_name", label: "Имя" },
    { key: "last_name", label: "Фамилия" },
    { key: "patronymic", label: "Отчество" },
    { key: "role_id", label: "Роль", type: "select" },
    { key: "lab_id", label: "Лаборатория", type: "select" },
    { key: "is_registrar", label: "Регистратор", type: "boolean" },
    { key: "is_lab_head", label: "Заведующий лабораторией", type: "boolean" },
    { key: "is_branch_head", label: "Руководитель филиала", type: "boolean" },
  ];

  return props.readOnly
    ? userFields
    : [
        ...userFields,
        {
          key: "password_hash",
          label: "Пароль",
          type: "password",
          required: props.mode === "create",
        },
      ];
});

const rolePermissionItems = computed<Permission[]>(() =>
  props.kind === "role" ? props.permissions ?? [] : [],
);

const userOverrideItems = computed<PermissionOverride[]>(() =>
  props.kind === "user" ? props.overrides ?? [] : [],
);

const auditEvents = computed(() => {
  const row = props.item;
  if (!row) return [];

  return [
    {
      id: "entity",
      label: props.kind === "role" ? "Роль" : "Пользователь",
      description: `Идентификатор: ${row.id}`,
      date: row.created_at ?? null,
    },
    {
      id: "update",
      label: "Последнее изменение",
      description: "Данные доступа сохранены через API.",
      date: row.updated_at ?? null,
    },
  ];
});

const eyebrow = computed(() =>
  `CRUD · ${props.kind === "role" ? "РОЛИ" : "ПОЛЬЗОВАТЕЛИ"}`,
);

watch(
  () => [props.open, props.item?.id] as const,
  ([open]) => {
    activeTab.value = "fields";
    if (!open) {
      Object.keys(form).forEach((key) => delete form[key]);
      return;
    }

    detailFields.value.forEach((field) => {
      form[field.key] = props.item?.[field.key] ?? (field.type === "boolean" ? false : "");
    });
  },
  { immediate: true },
);

function submit() {
  if (activeTab.value === "fields" && formRef.value && !formRef.value.reportValidity()) {
    return;
  }

  emit("save", { ...form });
}

function close() {
  emit("update:open", false);
}

function formatValue(value: unknown) {
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function formatFieldValue(field: DetailField) {
  const value = form[field.key];
  if (field.type === "select") {
    return fieldOptionsFor(field.key).find((option) => option.value === value)?.label ?? formatValue(value);
  }

  return formatValue(value);
}

function formString(key: string) {
  const value = form[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}

function formBoolean(key: string) {
  return Boolean(form[key]);
}

function setFormValue(key: string, value: unknown) {
  form[key] = value;
}

function fieldOptionsFor(key: string) {
  return props.fieldOptions?.[key] ?? [];
}

function formOptionValue(key: string) {
  const value = form[key];
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean" || value === null
    ? value
    : undefined;
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
      <div v-if="item || mode === 'create'" class="flex h-full flex-col overflow-hidden bg-default">
        <header class="border-b border-default px-5 py-4">
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <p class="truncate text-xs font-semibold uppercase tracking-wide text-muted">
                {{ eyebrow }}
              </p>
              <h2 class="mt-1 truncate text-2xl font-semibold text-highlighted">
                {{ title }}
              </h2>
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
              <UButton
                v-if="readOnly && editable"
                label="Редактировать"
                icon="i-lucide-pencil"
                color="neutral"
                variant="outline"
                size="sm"
                @click="emit('edit')"
              />
            </div>

            <form
              ref="formRef"
              class="overflow-hidden rounded-lg border border-default"
              @submit.prevent="submit"
            >
              <dl class="grid text-sm md:grid-cols-2">
                <div
                  v-for="field in detailFields"
                  :key="field.key"
                  class="grid grid-cols-[9.5rem_minmax(0,1fr)] border-b border-default last:border-b-0 md:[&:nth-last-child(-n+2)]:border-b-0 md:odd:border-e"
                >
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    {{ field.label }}
                  </dt>
                  <dd class="min-w-0 px-3 py-2 text-muted">
                    <USwitch
                      v-if="field.type === 'boolean' && !readOnly"
                      :model-value="formBoolean(field.key)"
                      @update:model-value="setFormValue(field.key, $event)"
                    />
                    <USelectMenu
                      v-else-if="field.type === 'select' && !readOnly"
                      :model-value="formOptionValue(field.key)"
                      :items="fieldOptionsFor(field.key)"
                      value-key="value"
                      label-key="label"
                      class="w-full"
                      clear
                      @update:model-value="setFormValue(field.key, $event)"
                    />
                    <UInput
                      v-else-if="!readOnly"
                      :model-value="formString(field.key)"
                      :type="field.type === 'password' ? 'password' : 'text'"
                      :required="field.required"
                      @update:model-value="setFormValue(field.key, $event)"
                    />
                    <span v-else class="block truncate">
                      {{ formatFieldValue(field) }}
                    </span>
                  </dd>
                </div>
              </dl>
            </form>
          </section>

          <section v-else-if="activeTab === 'permissions'" class="min-h-0">
            <div class="mb-3 flex items-center justify-between gap-3">
              <h3 class="text-sm font-semibold text-highlighted">
                {{ kind === 'user' ? 'Права и роли' : 'Права роли' }}
              </h3>
              <UBadge
                color="neutral"
                variant="outline"
                :label="kind === 'user' ? `${overrides?.length || 0} overrides` : `${permissions?.length || 0} прав`"
              />
            </div>
            <div
              v-if="loading"
              class="py-8 text-center text-sm text-toned"
            >
              Загрузка прав...
            </div>
            <PermissionEditor
              v-else
              :mode="kind === 'role' ? 'permissions' : 'overrides'"
              :permissions="rolePermissionItems"
              :role-permissions="rolePermissions"
              :overrides="userOverrideItems"
              :read-only="readOnly"
              @update:permissions="emit('update:permissions', $event)"
              @update:overrides="emit('update:overrides', $event)"
            />
          </section>

          <section v-else class="max-w-3xl">
            <div class="mb-3 flex items-center justify-between gap-3">
              <h3 class="text-sm font-semibold text-highlighted">
                Технический аудит
              </h3>
              <UBadge
                color="neutral"
                variant="outline"
                :label="`${auditEvents.length} события`"
              />
            </div>
            <div class="space-y-4 border-l border-default pl-5">
              <div v-for="event in auditEvents" :key="event.id" class="relative">
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
        </main>

        <footer class="flex justify-end gap-2 border-t border-default bg-elevated/40 px-5 py-3">
          <UButton
            label="Закрыть"
            color="neutral"
            variant="outline"
            :disabled="saving"
            @click="close"
          />
          <UButton
            v-if="!readOnly"
            label="Сохранить"
            icon="i-lucide-save"
            :loading="saving"
            @click="submit"
          />
        </footer>
      </div>
    </template>
  </UModal>
</template>
