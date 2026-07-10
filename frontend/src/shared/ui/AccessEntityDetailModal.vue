<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { TabsItem } from "@nuxt/ui";
import { useEntityForm } from "@/shared/composables/useEntityForm";
import EntityDetailModalShell, { type DetailListItem } from "@/shared/ui/EntityDetailModalShell.vue";
import EntityFieldGrid, { type FieldOption, type GridField } from "@/shared/ui/EntityFieldGrid.vue";
import PermissionEditor from "@/shared/ui/PermissionEditor.vue";
import TechnicalAuditTimeline from "@/shared/ui/TechnicalAuditTimeline.vue";
import { buildFallbackAuditEvents } from "@/shared/ui/entity-technical-audit";
import type { Permission, PermissionOverride } from "@/shared/types/permissions";

type AccessKind = "user" | "role";

type AccessRow = {
  id: string | number;
  [key: string]: unknown;
};

type AccessMode = "view" | "edit" | "create";

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
  breadcrumbs?: Array<{ label: string }>;
}>();

const emit = defineEmits<{
  (event: "update:open", value: boolean): void;
  (event: "save", payload: Record<string, unknown>): void;
  (event: "edit"): void;
  (event: "update:permissions", value: Permission[]): void;
  (event: "update:overrides", value: PermissionOverride[]): void;
  (event: "select", id: string | number): void;
  (event: "list-load-more"): void;
  (event: "go-to-level", index: number): void;
  (event: "open-related", payload: { id: string | number; label: string }): void;
}>();

const activeTab = ref("fields");
const formRef = ref<HTMLFormElement | null>(null);
const { formState, sync, reset, setValue } = useEntityForm();

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

const gridFields = computed<GridField[]>(() =>
  detailFields.value.map((field) => ({
    key: field.key,
    label: field.label,
    type: field.type,
    required: field.required,
    // Select-поля в этой модалке всегда допускают сброс значения (как раньше
    // безусловный атрибут `clear` на USelectMenu).
    clearable: field.type === "select",
  })),
);

const rolePermissionItems = computed<Permission[]>(() =>
  props.kind === "role" ? props.permissions ?? [] : [],
);

const userOverrideItems = computed<PermissionOverride[]>(() =>
  props.kind === "user" ? props.overrides ?? [] : [],
);

const auditEvents = computed(() => {
  const row = props.item;
  if (!row) return [];

  return buildFallbackAuditEvents(row, {
    stateLabel: accessStateLabel(row),
    savedDescription: "Данные доступа сохранены через API.",
  });
});

const eyebrow = computed(() =>
  `CRUD · ${props.kind === "role" ? "РОЛИ" : "ПОЛЬЗОВАТЕЛИ"}`,
);

watch(
  () => [props.open, props.item?.id] as const,
  ([open]) => {
    activeTab.value = "fields";
    if (!open) {
      reset();
      return;
    }

    sync(detailFields.value, props.item);
    // Create-режим: у нетронутых полей сохраняем прежние дефолты payload
    // (boolean → false, остальные → ""), а не null из normalizeFormValue.
    if (!props.item) {
      detailFields.value.forEach((field) => {
        if (formState[field.key] === null) {
          setValue(field.key, field.type === "boolean" ? false : "");
        }
      });
    }
  },
  { immediate: true },
);

function submit() {
  if (activeTab.value === "fields" && formRef.value && !formRef.value.reportValidity()) {
    return;
  }

  emit("save", { ...formState });
}

function close() {
  emit("update:open", false);
}

function formatValue(value: unknown) {
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function fieldOptionsFor(key: string) {
  return props.fieldOptions?.[key] ?? [];
}

// Повторяет прежний formatFieldValue: значение select резолвится в подпись
// опции, остальные поля — через formatValue.
function resolveFieldDisplay(field: GridField) {
  const value = formState[field.key];
  if (field.type === "select") {
    return fieldOptionsFor(field.key).find((option) => option.value === value)?.label ?? formatValue(value);
  }

  return formatValue(value);
}

function openRole() {
  const label =
    fieldOptionsFor("role_id").find((option) => option.value === formState.role_id)?.label
    ?? String(formState.role_id);
  emit("open-related", { id: formState.role_id as string | number, label });
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
    :breadcrumbs="breadcrumbs"
    @update:open="emit('update:open', $event)"
    @select="emit('select', $event)"
    @list-load-more="emit('list-load-more')"
    @go-to-level="emit('go-to-level', $event)"
  >
    <template #header-actions>
      <UButton
        v-if="kind === 'user' && readOnly && formState.role_id"
        label="Открыть роль"
        icon="i-lucide-shield"
        color="neutral"
        variant="outline"
        size="sm"
        @click="openRole"
      />
    </template>

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
        @submit.prevent="submit"
      >
        <EntityFieldGrid
          :fields="gridFields"
          :editing="!readOnly"
          :form-state="formState"
          :reference-options="fieldOptions"
          :resolve-display="resolveFieldDisplay"
          @update="setValue"
        />
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
