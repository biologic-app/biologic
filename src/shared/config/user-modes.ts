import type { Action, Resource } from "@/shared/types/permissions";
import { crudActions } from "@/shared/constants/permissions";

/**
 * Режимы пользователя (frontend-пресеты).
 *
 * Фаза «фронт сначала»: права разграничиваются на клиенте по активному режиму.
 * Источник истины для `can()` — пресеты ниже. Позже эти наборы будут заменены
 * реальными правами роли с бэкенда (см. useAuth.effectivePermissions), а сам
 * переключатель режима — ограничен ролью администратора.
 */
export type UserModeId =
  | "developer"          // РАЗ — полный доступ
  | "user_admin"         // АП  — управление пользователями и ролями
  | "registrar"          // РЕГ — приёмка образцов, направления, протоколы
  | "sanitary_inspector" // СВ  — санитарный врач (только просмотр своих)
  | "lab_doctor"         // ВЛ  — врач-лаборант (исследования и тесты)
  | "lab_assistant"      // АЛ  — ассистент-лаборант (только просмотр)
  | "lab_chief"          // НЛ  — начальник лаборатории
  | "branch_chief";      // НФ  — начальник филиала

/** Правило режима. Поддерживает wildcard `*` для ресурса и/или действия. */
export interface ModePermission {
  resource: Resource | "*";
  action: Action | "*";
}

export interface UserMode {
  id: UserModeId;
  /** i18n-ключ человекочитаемого названия (modes.<id>.label). */
  labelKey: string;
  /** i18n-ключ краткого описания (modes.<id>.description). */
  descriptionKey: string;
  icon: string;
  permissions: ModePermission[];
}

/** CRUD-права для ресурса (по умолчанию все четыре действия). */
const crud = (
  resource: Resource,
  actions: Action[] = [...crudActions],
): ModePermission[] => actions.map((action) => ({ resource, action }));

/** Одно командное право. */
const cmd = (resource: Resource, action: Action): ModePermission => ({
  resource,
  action,
});

/** Право только на просмотр перечня ресурсов. */
const viewOnly = (resources: Resource[]): ModePermission[] =>
  resources.map((resource) => ({ resource, action: "view" as Action }));

// ─── Наборы прав по ролям ──────────────────────────────────────────────────

// РАЗ — разработчик: полный доступ
const developer: ModePermission[] = [{ resource: "*", action: "*" }];

// АП — администратор пользователей: только управление доступом
const userAdmin: ModePermission[] = [
  { resource: "dashboard", action: "view" },
  ...crud("users"),
  ...crud("user-types"),
];

// РЕГ — регистратор: приёмка, направления, образцы, протоколы, справочники
const registrar: ModePermission[] = [
  { resource: "dashboard", action: "view" },
  ...crud("directions", ["view", "create", "edit"]),
  cmd("directions", "import"),
  cmd("directions", "register"),
  cmd("directions", "release"),
  ...crud("samples", ["view", "create", "edit"]),
  cmd("samples", "register"),
  cmd("samples", "reject"),
  ...crud("research", ["view", "create"]),
  cmd("research", "reject"),
  ...crud("protocols", ["view", "create", "edit"]),
  ...crud("conclusions", ["view", "create", "edit"]),
  ...crud("objects", ["view", "create", "edit"]),
  { resource: "labs", action: "view" },
  { resource: "users", action: "view" },
  ...viewOnly(["sample-types", "statuses", "protocol-types", "indicators", "research-goals"]),
];

// СВ — санитарный врач: просмотр своих направлений/образцов/исследований
const sanitaryInspector: ModePermission[] = [
  { resource: "dashboard", action: "view" },
  { resource: "directions", action: "view" },
  { resource: "samples", action: "view" },
  { resource: "research", action: "view" },
  { resource: "protocols", action: "view" },
  ...viewOnly(["sample-types", "statuses", "protocol-types"]),
];

// ВЛ — врач-лаборант: исследования и испытания своей лаборатории
const labDoctor: ModePermission[] = [
  { resource: "dashboard", action: "view" },
  { resource: "directions", action: "view" },
  { resource: "samples", action: "view" },
  cmd("samples", "reject"),
  { resource: "research", action: "view" },
  cmd("research", "confirm"),
  cmd("research", "start"),
  cmd("research", "reject"),
  { resource: "tests", action: "view" },
  cmd("tests", "start"),
  cmd("tests", "complete"),
  cmd("tests", "requeue"),
  cmd("tests", "reject"),
  { resource: "protocols", action: "view" },
  ...viewOnly(["sample-types", "statuses", "protocol-types", "research-goals", "indicators"]),
];

// АЛ — ассистент-лаборант: только просмотр рабочих объектов лаборатории
const labAssistant: ModePermission[] = [
  { resource: "dashboard", action: "view" },
  { resource: "directions", action: "view" },
  { resource: "samples", action: "view" },
  { resource: "research", action: "view" },
  { resource: "tests", action: "view" },
  ...viewOnly(["sample-types", "statuses", "research-goals", "indicators"]),
];

// НЛ — начальник лаборатории: всё что ВЛ + закрытие образцов + CRUD справочников
const labChief: ModePermission[] = [
  { resource: "dashboard", action: "view" },
  { resource: "directions", action: "view" },
  { resource: "samples", action: "view" },
  cmd("samples", "reject"),
  cmd("samples", "close"),
  { resource: "research", action: "view" },
  cmd("research", "confirm"),
  cmd("research", "start"),
  cmd("research", "reject"),
  { resource: "tests", action: "view" },
  cmd("tests", "start"),
  cmd("tests", "complete"),
  cmd("tests", "requeue"),
  cmd("tests", "reject"),
  { resource: "protocols", action: "view" },
  ...crud("indicators"),
  ...crud("research-goals"),
  ...viewOnly(["sample-types", "statuses", "protocol-types"]),
];

// НФ — начальник филиала: обзор филиала, нет исследований/тестов/заключений
const branchChief: ModePermission[] = [
  { resource: "dashboard", action: "view" },
  { resource: "directions", action: "view" },
  { resource: "samples", action: "view" },
  { resource: "protocols", action: "view" },
  { resource: "labs", action: "view" },
  { resource: "users", action: "view" },
  ...viewOnly(["sample-types", "statuses", "protocol-types"]),
];

// ─── Реестр режимов ────────────────────────────────────────────────────────

export const userModes: Record<UserModeId, UserMode> = {
  developer: {
    id: "developer",
    labelKey: "modes.developer.label",
    descriptionKey: "modes.developer.description",
    icon: "i-lucide-code",
    permissions: developer,
  },
  user_admin: {
    id: "user_admin",
    labelKey: "modes.user_admin.label",
    descriptionKey: "modes.user_admin.description",
    icon: "i-lucide-shield-check",
    permissions: userAdmin,
  },
  registrar: {
    id: "registrar",
    labelKey: "modes.registrar.label",
    descriptionKey: "modes.registrar.description",
    icon: "i-lucide-clipboard-pen",
    permissions: registrar,
  },
  sanitary_inspector: {
    id: "sanitary_inspector",
    labelKey: "modes.sanitary_inspector.label",
    descriptionKey: "modes.sanitary_inspector.description",
    icon: "i-lucide-stethoscope",
    permissions: sanitaryInspector,
  },
  lab_doctor: {
    id: "lab_doctor",
    labelKey: "modes.lab_doctor.label",
    descriptionKey: "modes.lab_doctor.description",
    icon: "i-lucide-flask-conical",
    permissions: labDoctor,
  },
  lab_assistant: {
    id: "lab_assistant",
    labelKey: "modes.lab_assistant.label",
    descriptionKey: "modes.lab_assistant.description",
    icon: "i-lucide-eye",
    permissions: labAssistant,
  },
  lab_chief: {
    id: "lab_chief",
    labelKey: "modes.lab_chief.label",
    descriptionKey: "modes.lab_chief.description",
    icon: "i-lucide-award",
    permissions: labChief,
  },
  branch_chief: {
    id: "branch_chief",
    labelKey: "modes.branch_chief.label",
    descriptionKey: "modes.branch_chief.description",
    icon: "i-lucide-building-2",
    permissions: branchChief,
  },
};

export const userModeList: UserMode[] = Object.values(userModes);

/** Режим по умолчанию: разработчик (полный доступ). */
export const defaultUserModeId: UserModeId = "developer";

export const isUserModeId = (value: unknown): value is UserModeId =>
  typeof value === "string" && value in userModes;

export const resolveUserMode = (id: UserModeId): UserMode =>
  userModes[id] ?? userModes[defaultUserModeId];

export const resolveModePermissions = (id: UserModeId): ModePermission[] =>
  resolveUserMode(id).permissions;

/** Проверка доступа по набору правил режима (с учётом wildcard `*`). */
export const modeAllows = (
  permissions: ModePermission[],
  resource: Resource,
  action: Action,
): boolean =>
  permissions.some(
    (permission) =>
      (permission.resource === "*" || permission.resource === resource) &&
      (permission.action === "*" || permission.action === action),
  );
