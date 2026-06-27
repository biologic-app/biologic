<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import type { TabsItem } from "@nuxt/ui";
import EntityDetailModalShell, { type DetailListItem } from "@/shared/ui/EntityDetailModalShell.vue";
import PermissionEditor from "@/shared/ui/PermissionEditor.vue";
import TechnicalAuditTimeline from "@/shared/ui/TechnicalAuditTimeline.vue";
import type { Permission, PermissionOverride } from "@/shared/types/permissions";

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
  listItems?: DetailListItem[];
  selectedId?: string | number | null;
  listHasMore?: boolean;
  listLoadingMore?: boolean;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "save", payload: Record<string, unknown>): void;
  (event: "edit"): void;
  (event: "update:permissions", value: Permission[]): void;
  (event: "update:overrides", value: PermissionOverride[]): void;
  (event: "select", id: string | number): void;
  (event: "list-load-more"): void;
}>();

const activeTab = ref("fields");
const formRef = ref<HTMLFormElement | null>(null);
const form = reactive<Record<string, unknown>>({});

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
      label: "Запись создана",
      description: `Код записи: ${entityDisplayCode(row.id)}`,
      actor: "system",
      date: auditDate(row.created_at),
    },
    {
      id: "update",
      label: "Последнее сохранение",
      description: "Данные доступа сохранены через API.",
      actor: "api",
      date: auditDate(row.updated_at),
    },
    {
      id: "status",
      label: "Текущее состояние",
      description: accessStateLabel(row),
      actor: "process",
      date: auditDate(row.updated_at ?? row.created_at),
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

function accessStateLabel(row: AccessRow) {
  if (typeof row.is_active === "boolean") {
    return row.is_active ? "Активна" : "Неактивна";
  }

  if (row.deleted_at) {
    return "Удалена";
  }

  return props.mode === "create" ? "Черновик" : "Актуальная запись";
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
  <EntityDetailModalShell
    v-model:active-tab="activeTab"
    :open="open"
    :eyebrow="eyebrow"
    :title="title"
    :tabs="tabs"
    size="lg"
    :list-items="listItems"
    :selected-id="selectedId"
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

    <TechnicalAuditTimeline v-else :events="auditEvents" />

    <template #footer>
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
    </template>
  </EntityDetailModalShell>
</template>
