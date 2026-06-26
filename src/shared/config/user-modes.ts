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
  | "admin"
  | "registrar"
  | "lab_head"
  | "branch_head"
  | "viewer";

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

const referenceResources: Resource[] = [
  "objects",
  "doctors",
  "branches",
  "labs",
  "sample-types",
  "statuses",
  "research-goals",
  "indicators",
  "protocol-types",
  "conclusions",
  "protocol-types",
];

const registrar: ModePermission[] = [
  { resource: "dashboard", action: "view" },
  ...crud("directions", ["view", "create", "edit"]),
  cmd("directions", "import"),
  cmd("directions", "register"),
  cmd("directions", "release"),
  ...crud("samples", ["view", "create", "edit"]),
  cmd("samples", "import"),
  cmd("samples", "register"),
  cmd("samples", "reject"),
  { resource: "research", action: "view" },
  { resource: "tests", action: "view" },
  { resource: "protocols", action: "view" },
  { resource: "results", action: "view" },
  ...viewOnly(referenceResources),
];

const labHead: ModePermission[] = [
  { resource: "dashboard", action: "view" },
  { resource: "directions", action: "view" },
  ...crud("research"),
  cmd("research", "confirm"),
  cmd("research", "start"),
  cmd("research", "complete"),
  ...crud("tests", ["view", "edit"]),
  cmd("tests", "start"),
  cmd("tests", "complete"),
  cmd("tests", "reject"),
  cmd("tests", "requeue"),
  { resource: "samples", action: "view" },
  cmd("samples", "close"),
  { resource: "results", action: "view" },
  cmd("results", "approve"),
  { resource: "conclusions", action: "view" },
  cmd("conclusions", "release"),
  { resource: "protocols", action: "view" },
  cmd("protocols", "release"),
  ...crud("indicators", ["view", "create", "edit"]),
  ...crud("research-goals", ["view", "create", "edit"]),
  ...viewOnly([
    "objects",
    "doctors",
    "branches",
    "labs",
    "sample-types",
    "statuses",
    "protocol-types",
  ]),
];

const branchHead: ModePermission[] = [
  { resource: "dashboard", action: "view" },
  // Обзор по всем сущностям филиала
  ...viewOnly([
    "directions",
    "research",
    "samples",
    "tests",
    "protocols",
    "results",
    "conclusions",
    "users",
    "user-types",
  ]),
  ...crud("branches"),
  ...crud("labs"),
  ...crud("objects"),
  ...crud("doctors"),
  cmd("directions", "register"),
  cmd("results", "approve"),
  cmd("conclusions", "release"),
  cmd("protocols", "release"),
];

export const userModes: Record<UserModeId, UserMode> = {
  admin: {
    id: "admin",
    labelKey: "modes.admin.label",
    descriptionKey: "modes.admin.description",
    icon: "i-lucide-shield-check",
    permissions: [{ resource: "*", action: "*" }],
  },
  registrar: {
    id: "registrar",
    labelKey: "modes.registrar.label",
    descriptionKey: "modes.registrar.description",
    icon: "i-lucide-clipboard-pen",
    permissions: registrar,
  },
  lab_head: {
    id: "lab_head",
    labelKey: "modes.lab_head.label",
    descriptionKey: "modes.lab_head.description",
    icon: "i-lucide-flask-conical",
    permissions: labHead,
  },
  branch_head: {
    id: "branch_head",
    labelKey: "modes.branch_head.label",
    descriptionKey: "modes.branch_head.description",
    icon: "i-lucide-building-2",
    permissions: branchHead,
  },
  viewer: {
    id: "viewer",
    labelKey: "modes.viewer.label",
    descriptionKey: "modes.viewer.description",
    icon: "i-lucide-eye",
    permissions: [{ resource: "*", action: "view" }],
  },
};

export const userModeList: UserMode[] = Object.values(userModes);

/** Режим по умолчанию: пока бэкенд не разграничивает права — полный доступ. */
export const defaultUserModeId: UserModeId = "admin";

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
