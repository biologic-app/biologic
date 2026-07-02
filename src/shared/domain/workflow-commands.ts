import type { FormField } from "@/shared/types/form";
import type { CrudRow } from "@/shared/types/crud";

export type WorkflowCommandKey =
  | "directions.register"
  | "samples.register"
  | "samples.reject"
  | "samples.close"
  | "research.confirm"
  | "research.start"
  | "research.reject"
  | "tests.start"
  | "tests.complete"
  | "tests.requeue"
  | "tests.reject";

export type WorkflowSelectionColor =
  | "primary"
  | "success"
  | "warning"
  | "error"
  | "neutral";

export type WorkflowCommand = {
  key: WorkflowCommandKey;
  label: string;
  title: string;
  icon: string;
  color?: WorkflowSelectionColor;
  // Презентация кнопки в панели массовых действий (SelectionActionBar).
  // Лейбл/цвет могут отличаться от title/color (короче, иной акцент).
  selection: { label: string; color: WorkflowSelectionColor };
  resource: "directions" | "samples" | "research" | "tests";
  action: "register" | "reject" | "close" | "confirm" | "start" | "complete" | "requeue";
  statuses: string[];
  endpoint: (row: CrudRow) => string;
  fields: FormField[];
  successTitle: string;
  errorTitle: string;
  body: (actorId: string, payload: Record<string, unknown>) => Record<string, unknown>;
};

export const workflowCommands: WorkflowCommand[] = [
  {
    key: "directions.register",
    label: "REG",
    title: "Зарегистрировать направление",
    icon: "i-lucide-clipboard-check",
    color: "primary",
    selection: { label: "Зарегистрировать", color: "primary" },
    resource: "directions",
    action: "register",
    statuses: ["draft"],
    endpoint: (row) => `/directions/${row.id}/register`,
    fields: [{ key: "comment", label: "Комментарий", type: "textarea" }],
    successTitle: "Направления зарегистрированы",
    errorTitle: "Не удалось зарегистрировать направления",
    body: (actorId, payload) => ({ actor_id: actorId, comment: payload.comment }),
  },
  {
    key: "samples.register",
    label: "REG",
    title: "Зарегистрировать образец",
    icon: "i-lucide-clipboard-check",
    color: "primary",
    selection: { label: "Зарегистрировать", color: "primary" },
    resource: "samples",
    action: "register",
    statuses: ["pending"],
    endpoint: (row) => `/samples/${row.id}/register`,
    fields: [
      { key: "received_at", label: "Дата получения", type: "date", required: true, layout: { span: 6 } },
      { key: "deadline", label: "Срок", type: "date", layout: { span: 6 } },
    ],
    successTitle: "Образцы зарегистрированы",
    errorTitle: "Не удалось зарегистрировать образцы",
    body: (actorId, payload) => ({
      actor_id: actorId,
      received_at: payload.received_at,
      deadline: payload.deadline,
    }),
  },
  {
    key: "samples.reject",
    label: "REJ",
    title: "Забраковать образец",
    icon: "i-lucide-ban",
    color: "error",
    selection: { label: "Брак", color: "warning" },
    resource: "samples",
    action: "reject",
    statuses: ["pending", "registered", "in_progress"],
    endpoint: (row) => `/samples/${row.id}/reject`,
    fields: [{ key: "reason", label: "Причина", type: "textarea", required: true }],
    successTitle: "Образцы помечены как брак",
    errorTitle: "Не удалось забраковать образцы",
    body: (actorId, payload) => ({ actor_id: actorId, reason: payload.reason }),
  },
  {
    key: "samples.close",
    label: "CLO",
    title: "Закрыть образец",
    icon: "i-lucide-lock-keyhole",
    color: "success",
    selection: { label: "Закрыть", color: "success" },
    resource: "samples",
    action: "close",
    statuses: ["analyzed"],
    endpoint: (row) => `/samples/${row.id}/close`,
    fields: [
      { key: "verdict", label: "Вердикт", required: true },
      { key: "comment", label: "Комментарий", type: "textarea" },
    ],
    successTitle: "Образцы закрыты",
    errorTitle: "Не удалось закрыть образцы",
    body: (actorId, payload) => ({
      actor_id: actorId,
      verdict: payload.verdict,
      comment: payload.comment,
    }),
  },
  {
    key: "research.confirm",
    label: "CNF",
    title: "Подтвердить исследование",
    icon: "i-lucide-check-check",
    color: "primary",
    selection: { label: "Подтвердить", color: "primary" },
    resource: "research",
    action: "confirm",
    statuses: ["draft"],
    endpoint: (row) => `/research/${row.id}/confirm`,
    fields: [],
    successTitle: "Исследования подтверждены",
    errorTitle: "Не удалось подтвердить исследования",
    body: (actorId) => ({ actor_id: actorId }),
  },
  {
    key: "research.start",
    label: "STR",
    title: "Взять исследование в работу",
    icon: "i-lucide-play",
    color: "primary",
    selection: { label: "В работу", color: "primary" },
    resource: "research",
    action: "start",
    statuses: ["ordered"],
    endpoint: (row) => `/research/${row.id}/start`,
    fields: [],
    successTitle: "Исследования взяты в работу",
    errorTitle: "Не удалось взять исследования в работу",
    body: (actorId) => ({ actor_id: actorId }),
  },
  {
    key: "research.reject",
    label: "REJ",
    title: "Отклонить исследование",
    icon: "i-lucide-ban",
    color: "error",
    selection: { label: "Отклонить", color: "error" },
    resource: "research",
    action: "reject",
    statuses: ["draft", "ordered"],
    endpoint: (row) => `/research/${row.id}/reject`,
    fields: [{ key: "reason", label: "Причина", type: "textarea", required: true }],
    successTitle: "Исследования отклонены",
    errorTitle: "Не удалось отклонить исследования",
    body: (actorId, payload) => ({ actor_id: actorId, reason: payload.reason }),
  },
  {
    key: "tests.start",
    label: "STR",
    title: "Взять тест в работу",
    icon: "i-lucide-play",
    color: "primary",
    selection: { label: "В работу", color: "primary" },
    resource: "tests",
    action: "start",
    statuses: ["queued"],
    endpoint: (row) => `/tests/${row.id}/start`,
    fields: [],
    successTitle: "Тесты взяты в работу",
    errorTitle: "Не удалось взять тесты в работу",
    body: (actorId) => ({ actor_id: actorId }),
  },
  {
    key: "tests.complete",
    label: "RES",
    title: "Внести результат теста",
    icon: "i-lucide-check",
    color: "success",
    selection: { label: "Результат", color: "success" },
    resource: "tests",
    action: "complete",
    statuses: ["in_progress"],
    endpoint: (row) => `/tests/${row.id}/complete`,
    fields: [
      { key: "value", label: "Значение", required: true, layout: { span: 6 } },
      { key: "norm", label: "Норма", layout: { span: 6 } },
      { key: "comment", label: "Комментарий", type: "textarea" },
    ],
    successTitle: "Результаты тестов сохранены",
    errorTitle: "Не удалось сохранить результаты тестов",
    body: (actorId, payload) => ({
      actor_id: actorId,
      value: payload.value,
      norm: payload.norm,
      comment: payload.comment,
    }),
  },
  {
    key: "tests.requeue",
    label: "REQ",
    title: "Вернуть тест в очередь",
    icon: "i-lucide-rotate-ccw",
    color: "warning",
    selection: { label: "В очередь", color: "warning" },
    resource: "tests",
    action: "requeue",
    statuses: ["in_progress"],
    endpoint: (row) => `/tests/${row.id}/requeue`,
    fields: [],
    successTitle: "Тесты возвращены в очередь",
    errorTitle: "Не удалось вернуть тесты в очередь",
    body: (actorId) => ({ actor_id: actorId }),
  },
  {
    key: "tests.reject",
    label: "REJ",
    title: "Отклонить тест",
    icon: "i-lucide-ban",
    color: "error",
    selection: { label: "Отклонить", color: "error" },
    resource: "tests",
    action: "reject",
    statuses: ["queued", "in_progress"],
    endpoint: (row) => `/tests/${row.id}/reject`,
    fields: [{ key: "reason", label: "Причина", type: "textarea", required: true }],
    successTitle: "Тесты отклонены",
    errorTitle: "Не удалось отклонить тесты",
    body: (actorId, payload) => ({ actor_id: actorId, reason: payload.reason }),
  },
];
