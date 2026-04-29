import type { WorkflowEntityAction, WorkflowScreenConfig, WorkspaceMode } from "@/shared/types";

export type WorkflowRoleKey =
  | "sanitary_inspector"
  | "registrar"
  | "lab_doctor"
  | "lab_assistant"
  | "lab_chief"
  | "branch_chief"
  | "user_admin";

export interface WorkflowMetric {
  label: string;
  value: string;
  tone: "neutral" | "primary" | "info" | "success" | "warning" | "error";
  icon: string;
}

export interface WorkflowQueue {
  title: string;
  description: string;
  count: number;
  status: string;
  route: string;
  icon: string;
  tone: "neutral" | "primary" | "info" | "success" | "warning" | "error";
}

export interface WorkflowAction {
  label: string;
  icon: string;
  route: string;
  primary?: boolean;
}

export interface WorkflowStep {
  title: string;
  description: string;
  status?: string;
}

export interface WorkflowRole {
  key: WorkflowRoleKey;
  shortName: string;
  title: string;
  subtitle: string;
  entryPoint: string;
  route: string;
  metrics: WorkflowMetric[];
  queues: WorkflowQueue[];
  actions: WorkflowAction[];
  flow: WorkflowStep[];
  screens: string[];
  constraints: string[];
}

export const roleWorkspaceModes: Record<WorkflowRoleKey, WorkspaceMode> = {
  sanitary_inspector: "readonly",
  registrar: "editable",
  lab_doctor: "editable",
  lab_assistant: "readonly",
  lab_chief: "closing",
  branch_chief: "readonly",
  user_admin: "admin",
};

export const workflowScreens: WorkflowScreenConfig[] = [
  {
    id: "directions-acceptance",
    title: "Очередь приёмки",
    route: "/directions",
    roles: ["registrar"],
    mode: "editable",
    defaultFilters: { status: "draft" },
    primaryActions: ["direction.import", "direction.create", "direction.register"],
  },
  {
    id: "directions-readonly",
    title: "Направления",
    route: "/directions",
    roles: ["sanitary_inspector", "branch_chief"],
    mode: "readonly",
    defaultFilters: { scope: "role" },
    primaryActions: ["direction.open", "protocol.open"],
  },
  {
    id: "research-workqueue",
    title: "Рабочая очередь",
    route: "/research",
    roles: ["lab_doctor", "lab_chief"],
    mode: "editable",
    defaultFilters: { status: "draft" },
    primaryActions: ["research.approve", "research.start", "test.result"],
  },
  {
    id: "research-readonly",
    title: "Лабораторная очередь",
    route: "/research",
    roles: ["lab_assistant"],
    mode: "readonly",
    defaultFilters: { mode: "readonly" },
    primaryActions: ["research.open"],
  },
  {
    id: "sample-closing",
    title: "Образцы на закрытие",
    route: "/research",
    roles: ["lab_chief"],
    mode: "closing",
    defaultFilters: { sample_status: "analyzed" },
    primaryActions: ["sample.close", "test.assign"],
  },
  {
    id: "alerts",
    title: "Уведомления",
    route: "/inbox",
    roles: ["sanitary_inspector", "branch_chief"],
    mode: "readonly",
    primaryActions: ["alert.hide", "direction.open"],
  },
  {
    id: "admin-users",
    title: "Пользователи и scopes",
    route: "/settings/members",
    roles: ["user_admin"],
    mode: "admin",
    defaultFilters: { scope: "missing" },
    primaryActions: ["user.create", "user.scope", "user.role"],
  },
  {
    id: "admin-security",
    title: "Роли и права",
    route: "/settings/security",
    roles: ["user_admin"],
    mode: "admin",
    primaryActions: ["role.permissions"],
  },
];

export const workflowEntityActions: WorkflowEntityAction[] = [
  { resource: "direction", action: "open", roles: ["sanitary_inspector", "registrar", "branch_chief"], label: "Открыть направление", icon: "i-lucide-book-open" },
  { resource: "direction", action: "import", toStatus: "draft", roles: ["registrar"], label: "Импортировать направление", icon: "i-lucide-upload" },
  { resource: "direction", action: "create", toStatus: "draft", roles: ["registrar"], label: "Создать направление", icon: "i-lucide-plus" },
  { resource: "direction", action: "register", fromStatus: "draft", toStatus: "registered", roles: ["registrar"], label: "Зарегистрировать направление", icon: "i-lucide-clipboard-check", confirmation: "Направление будет передано в лаборатории." },
  { resource: "sample", action: "register", fromStatus: "pending", toStatus: "registered", roles: ["registrar"], label: "Принять образец", icon: "i-lucide-vial" },
  { resource: "sample", action: "reject", fromStatus: "pending", toStatus: "rejected", roles: ["registrar", "lab_doctor", "lab_chief"], label: "Отклонить как брак", icon: "i-lucide-ban", confirmation: "Связанные исследования будут отклонены." },
  { resource: "protocol", action: "create", fromStatus: "completed", toStatus: "issued", roles: ["registrar"], label: "Создать протокол", icon: "i-lucide-file-signature" },
  { resource: "protocol", action: "open", roles: ["sanitary_inspector", "registrar", "branch_chief"], label: "Открыть протокол", icon: "i-lucide-file-check-2" },
  { resource: "research", action: "approve", fromStatus: "draft", toStatus: "ordered", roles: ["lab_doctor", "lab_chief"], label: "Подтвердить исследование", icon: "i-lucide-clipboard-check" },
  { resource: "research", action: "start", fromStatus: "ordered", toStatus: "in_progress", roles: ["lab_doctor", "lab_chief"], label: "Взять в работу", icon: "i-lucide-play" },
  { resource: "test", action: "result", fromStatus: "in_progress", toStatus: "completed", roles: ["lab_doctor", "lab_chief"], label: "Внести результат", icon: "i-lucide-pencil-line" },
  { resource: "sample", action: "close", fromStatus: "analyzed", toStatus: "completed", roles: ["lab_chief"], label: "Закрыть образец", icon: "i-lucide-badge-check", confirmation: "После закрытия образец попадёт в протокол." },
  { resource: "test", action: "assign", roles: ["lab_chief"], label: "Назначить испытание", icon: "i-lucide-list-plus" },
  { resource: "alert", action: "hide", roles: ["sanitary_inspector", "branch_chief"], label: "Скрыть уведомление", icon: "i-lucide-eye-off" },
  { resource: "user", action: "create", roles: ["user_admin"], label: "Создать пользователя", icon: "i-lucide-user-plus" },
  { resource: "user", action: "scope", roles: ["user_admin"], label: "Настроить scope", icon: "i-lucide-user-cog" },
  { resource: "user", action: "role", roles: ["user_admin"], label: "Назначить роль", icon: "i-lucide-shield" },
  { resource: "user", action: "delete", roles: ["user_admin"], label: "Soft-delete", icon: "i-lucide-trash-2", confirmation: "Пользователь будет скрыт из активного списка." },
];

export const workflowRoles: WorkflowRole[] = [
  {
    key: "registrar",
    shortName: "РЕГ",
    title: "Регистратор",
    subtitle: "Приёмка, регистрация образцов, направления и протоколы.",
    entryPoint: "Очередь приёмки",
    route: "/directions",
    metrics: [
      { label: "Ожидают приёмки", value: "18", tone: "warning", icon: "i-lucide-inbox" },
      { label: "На регистрации", value: "42", tone: "primary", icon: "i-lucide-clipboard-list" },
      { label: "Просрочено", value: "7", tone: "error", icon: "i-lucide-triangle-alert" },
      { label: "Готово к протоколу", value: "11", tone: "success", icon: "i-lucide-file-check-2" },
    ],
    queues: [
      {
        title: "Направления draft",
        description: "Заполнить типы образцов и назначить лаборатории.",
        count: 18,
        status: "draft",
        route: "/directions?status=draft",
        icon: "i-lucide-book-copy",
        tone: "warning",
      },
      {
        title: "Образцы pending",
        description: "Принять, проставить received_at или отметить брак.",
        count: 42,
        status: "pending",
        route: "/directions?sample_status=pending",
        icon: "i-lucide-vial",
        tone: "primary",
      },
      {
        title: "Протоколы к выпуску",
        description: "Все образцы закрыты, можно собрать протокол.",
        count: 11,
        status: "completed",
        route: "/directions?status=completed&protocol=missing",
        icon: "i-lucide-file-signature",
        tone: "success",
      },
    ],
    actions: [
      { label: "Импортировать направление", icon: "i-lucide-upload", route: "/directions?flow=import", primary: true },
      { label: "Создать вручную", icon: "i-lucide-plus", route: "/directions?flow=create" },
      { label: "Открыть очередь", icon: "i-lucide-list-checks", route: "/directions?status=draft" },
    ],
    flow: [
      { title: "Импорт или ручное создание", description: "Направление появляется в статусе draft.", status: "— -> draft" },
      { title: "Подготовка направления", description: "Проставить типы образцов и лаборатории.", status: "draft" },
      { title: "Регистрация", description: "Перевести направление в registered и принять образцы.", status: "draft -> registered" },
      { title: "Брак или работа", description: "Отклонить непригодные образцы или передать их в лаборатории.", status: "pending -> registered/rejected" },
      { title: "Протокол", description: "После закрытия всех образцов сформировать протокол и заключение.", status: "completed" },
    ],
    screens: ["Dashboard", "Очередь приёмки", "Карточка направления", "Форма образца", "Конструктор протокола"],
    constraints: ["Редактирование направления доступно только в draft.", "Брак образца автоматически отклоняет связанные исследования."],
  },
  {
    key: "lab_doctor",
    shortName: "ВЛ",
    title: "Врач-лаборант",
    subtitle: "Подтверждение исследований и выполнение испытаний своей лаборатории.",
    entryPoint: "Рабочая очередь",
    route: "/research",
    metrics: [
      { label: "На подтверждении", value: "9", tone: "warning", icon: "i-lucide-clipboard-check" },
      { label: "В работе", value: "23", tone: "primary", icon: "i-lucide-flask-conical" },
      { label: "Просрочено", value: "5", tone: "error", icon: "i-lucide-timer-off" },
      { label: "Выполнено", value: "64", tone: "success", icon: "i-lucide-circle-check" },
    ],
    queues: [
      {
        title: "Исследования draft",
        description: "Подтвердить или отклонить назначенные исследования.",
        count: 9,
        status: "draft",
        route: "/research?status=draft",
        icon: "i-lucide-search-check",
        tone: "warning",
      },
      {
        title: "Исследования in_progress",
        description: "Внести результаты испытаний или вернуть испытания в очередь.",
        count: 23,
        status: "in_progress",
        route: "/research?status=in_progress",
        icon: "i-lucide-flask-conical",
        tone: "primary",
      },
      {
        title: "Срочные образцы",
        description: "Образцы с высоким приоритетом и близким дедлайном.",
        count: 6,
        status: "urgent",
        route: "/research?priority=urgent",
        icon: "i-lucide-siren",
        tone: "error",
      },
    ],
    actions: [
      { label: "Открыть подтверждение", icon: "i-lucide-clipboard-check", route: "/research?status=draft", primary: true },
      { label: "Внести результат", icon: "i-lucide-pencil-line", route: "/research?status=in_progress" },
      { label: "Просрочки", icon: "i-lucide-triangle-alert", route: "/research?deadline=overdue" },
    ],
    flow: [
      { title: "Подтвердить исследование", description: "Перевести draft в ordered или отклонить.", status: "draft -> ordered/rejected" },
      { title: "Взять в работу", description: "Начать выполнение исследования.", status: "ordered -> in_progress" },
      { title: "Выполнить испытания", description: "Старт, результат, возврат в очередь или отклонение испытаний.", status: "queued/in_progress" },
      { title: "Автозавершение", description: "После финальных испытаний система завершает исследование.", status: "in_progress -> completed" },
    ],
    screens: ["Dashboard", "Research master-detail", "Карточка исследования", "Форма испытания", "История статусов"],
    constraints: ["Доступ ограничен своей лабораторией.", "Действия показываются только для допустимого статуса."],
  },
  {
    key: "lab_chief",
    shortName: "НЛ",
    title: "Начальник лаборатории",
    subtitle: "Контроль лаборатории, закрытие образцов и ведение лабораторных справочников.",
    entryPoint: "Образцы на закрытие",
    route: "/research?queue=closing",
    metrics: [
      { label: "На подтверждении", value: "12", tone: "warning", icon: "i-lucide-clipboard-check" },
      { label: "На закрытие", value: "14", tone: "primary", icon: "i-lucide-badge-check" },
      { label: "Просрочено", value: "4", tone: "error", icon: "i-lucide-triangle-alert" },
      { label: "Браков", value: "3", tone: "error", icon: "i-lucide-ban" },
    ],
    queues: [
      {
        title: "Исследования draft",
        description: "Подтвердить или отклонить исследования лаборатории.",
        count: 12,
        status: "draft",
        route: "/research?status=draft",
        icon: "i-lucide-search-check",
        tone: "warning",
      },
      {
        title: "Образцы analyzed",
        description: "Проверить историю, установить verdict и закрыть.",
        count: 14,
        status: "analyzed",
        route: "/research?sample_status=analyzed",
        icon: "i-lucide-badge-check",
        tone: "primary",
      },
      {
        title: "Справочники лаборатории",
        description: "Цели исследований и показатели своей лаборатории.",
        count: 2,
        status: "references",
        route: "/settings",
        icon: "i-lucide-library",
        tone: "neutral",
      },
    ],
    actions: [
      { label: "Образцы на закрытие", icon: "i-lucide-badge-check", route: "/research?sample_status=analyzed", primary: true },
      { label: "Подтверждение", icon: "i-lucide-clipboard-check", route: "/research?status=draft" },
      { label: "Справочники", icon: "i-lucide-library", route: "/settings" },
    ],
    flow: [
      { title: "Подтверждение", description: "Подтвердить или отклонить исследования.", status: "draft -> ordered/rejected" },
      { title: "Работа лаборатории", description: "При необходимости выполнять действия врача-лаборанта.", status: "ordered/in_progress" },
      { title: "Закрытие образца", description: "Установить verdict и закрыть образец.", status: "analyzed -> completed" },
      { title: "Новые испытания", description: "Назначение новых испытаний возвращает объект в работу.", status: "completed -> in_progress" },
    ],
    screens: ["Dashboard", "Очередь подтверждения", "Список на закрытие", "Карточка образца", "Справочники лаборатории"],
    constraints: ["Закрытие completed требует подтверждения.", "НЛ видит и действия ВЛ, и собственные действия закрытия."],
  },
  {
    key: "sanitary_inspector",
    shortName: "СВ",
    title: "Санитарный врач",
    subtitle: "Контроль своих направлений, образцов и готовых протоколов.",
    entryPoint: "Мои направления",
    route: "/directions?scope=own",
    metrics: [
      { label: "Активных направлений", value: "16", tone: "primary", icon: "i-lucide-book-open-check" },
      { label: "Ожидают результатов", value: "31", tone: "warning", icon: "i-lucide-hourglass" },
      { label: "Завершено", value: "22", tone: "success", icon: "i-lucide-circle-check" },
      { label: "Готовых протоколов", value: "8", tone: "info", icon: "i-lucide-file-check-2" },
    ],
    queues: [
      {
        title: "Мои активные направления",
        description: "Статусы registered, in_progress, partially_completed.",
        count: 16,
        status: "active",
        route: "/directions?scope=own&status=active",
        icon: "i-lucide-book-open-check",
        tone: "primary",
      },
      {
        title: "Готовые протоколы",
        description: "Протоколы, доступные к просмотру.",
        count: 8,
        status: "ready",
        route: "/directions?scope=own&protocol=ready",
        icon: "i-lucide-file-check-2",
        tone: "success",
      },
    ],
    actions: [
      { label: "Мои направления", icon: "i-lucide-book-open-check", route: "/directions?scope=own", primary: true },
      { label: "Готовые протоколы", icon: "i-lucide-file-check-2", route: "/directions?protocol=ready" },
      { label: "Уведомления", icon: "i-lucide-bell", route: "/inbox" },
    ],
    flow: [
      { title: "Передать образцы", description: "Образцы и электронное направление передаются регистратору." },
      { title: "Отслеживать статус", description: "После импорта доступны направление, образцы и прогресс." },
      { title: "Получить протокол", description: "После завершения исследований открыть готовый протокол." },
    ],
    screens: ["Dashboard", "Мои направления", "Карточка направления", "Протокол", "Уведомления"],
    constraints: ["Только чтение.", "Данные ограничены своими объектами."],
  },
  {
    key: "lab_assistant",
    shortName: "АЛ",
    title: "Ассистент-лаборант",
    subtitle: "Наблюдение за образцами, исследованиями и испытаниями своей лаборатории.",
    entryPoint: "Дашборд лаборатории",
    route: "/research?mode=readonly",
    metrics: [
      { label: "Активных образцов", value: "38", tone: "primary", icon: "i-lucide-vial" },
      { label: "Исследований в работе", value: "21", tone: "info", icon: "i-lucide-flask-conical" },
      { label: "Просрочено", value: "5", tone: "error", icon: "i-lucide-timer-off" },
      { label: "Выполнено", value: "57", tone: "success", icon: "i-lucide-circle-check" },
    ],
    queues: [
      {
        title: "Активные образцы",
        description: "Read-only список образцов своей лаборатории.",
        count: 38,
        status: "active",
        route: "/research?mode=readonly&sample_status=active",
        icon: "i-lucide-vial",
        tone: "primary",
      },
      {
        title: "Просроченные",
        description: "Позиции, требующие внимания врача или начальника лаборатории.",
        count: 5,
        status: "overdue",
        route: "/research?mode=readonly&deadline=overdue",
        icon: "i-lucide-triangle-alert",
        tone: "error",
      },
    ],
    actions: [
      { label: "Открыть лабораторию", icon: "i-lucide-flask-conical", route: "/research?mode=readonly", primary: true },
      { label: "Просроченные", icon: "i-lucide-triangle-alert", route: "/research?deadline=overdue" },
    ],
    flow: [
      { title: "Открыть лабораторию", description: "Просмотреть текущие образцы и исследования." },
      { title: "Найти проблему", description: "Отфильтровать просрочки или активные исследования." },
      { title: "Передать информацию", description: "Сообщить врачу-лаборанту или НЛ вне системы." },
    ],
    screens: ["Dashboard", "Read-only Research", "Карточка образца", "История статусов"],
    constraints: ["Нет уведомлений.", "Все операционные кнопки скрыты."],
  },
  {
    key: "branch_chief",
    shortName: "НФ",
    title: "Начальник филиала",
    subtitle: "Контроль филиала и критических событий без операционного вмешательства.",
    entryPoint: "Критические уведомления",
    route: "/inbox",
    metrics: [
      { label: "Активных направлений", value: "54", tone: "primary", icon: "i-lucide-book-copy" },
      { label: "Просрочено", value: "9", tone: "error", icon: "i-lucide-triangle-alert" },
      { label: "Браков", value: "6", tone: "error", icon: "i-lucide-ban" },
      { label: "Выполнено", value: "71", tone: "success", icon: "i-lucide-circle-check" },
    ],
    queues: [
      {
        title: "Критические события",
        description: "Брак, не соответствует, просроченные дедлайны.",
        count: 15,
        status: "critical",
        route: "/inbox?severity=critical",
        icon: "i-lucide-siren",
        tone: "error",
      },
      {
        title: "Направления филиала",
        description: "Read-only контроль по лабораториям филиала.",
        count: 54,
        status: "active",
        route: "/directions?scope=branch",
        icon: "i-lucide-book-copy",
        tone: "primary",
      },
    ],
    actions: [
      { label: "Критические уведомления", icon: "i-lucide-siren", route: "/inbox?severity=critical", primary: true },
      { label: "Просроченные", icon: "i-lucide-triangle-alert", route: "/directions?deadline=overdue" },
      { label: "Браки", icon: "i-lucide-ban", route: "/directions?sample_status=rejected" },
    ],
    flow: [
      { title: "Получить сигнал", description: "Открыть уведомление о браке, просрочке или verdict." },
      { title: "Проверить карточку", description: "Перейти к направлению или образцу филиала." },
      { title: "Контролировать динамику", description: "Смотреть сводку по филиалу без изменения данных." },
    ],
    screens: ["Dashboard", "Критические уведомления", "Направления филиала", "Карточка направления"],
    constraints: ["Нет доступа к research/tests.", "Операционные действия скрыты."],
  },
  {
    key: "user_admin",
    shortName: "АП",
    title: "Администратор пользователей",
    subtitle: "Пользователи, роли, разрешения и области видимости.",
    entryPoint: "Пользователи без scope",
    route: "/settings/members",
    metrics: [
      { label: "Пользователей", value: "128", tone: "primary", icon: "i-lucide-users" },
      { label: "Новых", value: "12", tone: "success", icon: "i-lucide-user-plus" },
      { label: "Ролей", value: "8", tone: "info", icon: "i-lucide-shield" },
      { label: "Без scope", value: "5", tone: "warning", icon: "i-lucide-user-cog" },
    ],
    queues: [
      {
        title: "Пользователи без scope",
        description: "Нужно назначить филиал, лабораторию или объект.",
        count: 5,
        status: "missing_scope",
        route: "/settings/members?scope=missing",
        icon: "i-lucide-user-cog",
        tone: "warning",
      },
      {
        title: "Роли и разрешения",
        description: "Проверить матрицу прав и назначенные permissions.",
        count: 8,
        status: "roles",
        route: "/settings/security",
        icon: "i-lucide-shield-check",
        tone: "info",
      },
    ],
    actions: [
      { label: "Создать пользователя", icon: "i-lucide-user-plus", route: "/settings/members?flow=create", primary: true },
      { label: "Настроить scope", icon: "i-lucide-user-cog", route: "/settings/members?scope=missing" },
      { label: "Роли и права", icon: "i-lucide-shield-check", route: "/settings/security" },
    ],
    flow: [
      { title: "Создать пользователя", description: "Заполнить учетные данные и выбрать роль." },
      { title: "Назначить scope", description: "Привязать пользователя к филиалу, лаборатории или объекту." },
      { title: "Проверить права", description: "При необходимости обновить permissions роли." },
    ],
    screens: ["Dashboard", "Пользователи", "Форма пользователя", "User scopes", "Roles & permissions"],
    constraints: ["Нет доступа к операционным данным.", "Пользователи без scope подсвечиваются отдельно."],
  },
];

export const defaultWorkflowRoleKey: WorkflowRoleKey = "registrar";

export function getWorkflowRole(key: WorkflowRoleKey): WorkflowRole {
  return workflowRoles.find((role) => role.key === key) ?? workflowRoles[0];
}
