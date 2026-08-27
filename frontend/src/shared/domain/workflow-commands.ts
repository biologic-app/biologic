import { i18n } from "@/shared/i18n";
import type { FormField } from "@/shared/types/form";
import type { CrudRow } from "@/shared/types/crud";

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString();

export type WorkflowCommandKey =
  | "directions.register"
  | "samples.register"
  | "samples.reject"
  | "samples.close"
  | "research.reject"
  | "tests.complete"
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
  action: "register" | "reject" | "close" | "complete";
  statuses: string[];
  endpoint: (row: CrudRow) => string;
  fields: FormField[];
  successTitle: string;
  errorTitle: string;
  body: (_actorId: string, payload: Record<string, unknown>) => Record<string, unknown>;
};

export const workflowCommands: WorkflowCommand[] = [
  {
    key: "directions.register",
    label: "REG",
    title: t("workflowCommands.registersDirection"),
    icon: "i-lucide-clipboard-check",
    color: "primary",
    selection: { label: t("workflowCommands.registerDirection"), color: "primary" },
    resource: "directions",
    action: "register",
    statuses: ["draft"],
    endpoint: (row) => `/directions/${row.id}/register`,
    fields: [{ key: "comment", label: t("workflowCommands.formFields.comment"), type: "textarea" }],
    successTitle: t("workflowCommands.directionsRegistered"),
    errorTitle: t("workflowCommands.failedToRegisterDirections"),
    body: (_actorId, payload) => ({ comment: payload.comment }),
  },
  {
    key: "samples.register",
    label: "REG",
    title: t("workflowCommands.registerSample"),
    icon: "i-lucide-clipboard-check",
    color: "primary",
    selection: { label: t("workflowCommands.registerSamples"), color: "primary" },
    resource: "samples",
    action: "register",
    statuses: ["pending"],
    endpoint: (row) => `/samples/${row.id}/register`,
    fields: [
      { key: "received_at", label: t("workflowCommands.formFields.receivedAt"), type: "date", required: true, layout: { span: 6 } },
      { key: "deadline", label: t("workflowCommands.formFields.deadline"), type: "date", layout: { span: 6 } },
    ],
    successTitle: t("workflowCommands.samplesRegistered"),
    errorTitle: t("workflowCommands.failedToRegisterSamples"),
    body: (_actorId, payload) => ({
      received_at: payload.received_at,
      deadline: payload.deadline,
    }),
  },
  {
    key: "samples.reject",
    label: "REJ",
    title: t("workflowCommands.rejectSample"),
    icon: "i-lucide-ban",
    color: "error",
    selection: { label: t("workflowCommands.rejectSamples"), color: "warning" },
    resource: "samples",
    action: "reject",
    statuses: ["registered", "in_progress"],
    endpoint: (row) => `/samples/${row.id}/reject`,
    fields: [{ key: "reason", label: t("workflowCommands.formFields.reason"), type: "textarea", required: true }],
    successTitle: t("workflowCommands.samplesRejected"),
    errorTitle: t("workflowCommands.failedToRejectSamples"),
    body: (_actorId, payload) => ({ reason: payload.reason }),
  },
  {
    key: "samples.close",
    label: "CLO",
    title: t("workflowCommands.closeSample"),
    icon: "i-lucide-lock-keyhole",
    color: "success",
    selection: { label: t("workflowCommands.closeSamples"), color: "success" },
    resource: "samples",
    action: "close",
    statuses: ["analyzed"],
    endpoint: (row) => `/samples/${row.id}/close`,
    fields: [
      { key: "verdict", label: t("workflowCommands.formFields.verdict"), required: true },
      { key: "comment", label: t("workflowCommands.formFields.comment"), type: "textarea" },
    ],
    successTitle: t("workflowCommands.samplesClosed"),
    errorTitle: t("workflowCommands.failedToCloseSamples"),
    body: (_actorId, payload) => ({
      verdict: payload.verdict,
      comment: payload.comment,
    }),
  },
  {
    key: "research.reject",
    label: "REJ",
    title: t("workflowCommands.rejectResearch"),
    icon: "i-lucide-ban",
    color: "error",
    selection: { label: t("workflowCommands.rejectResearch_selection"), color: "error" },
    resource: "research",
    action: "reject",
    statuses: ["in_progress"],
    endpoint: (row) => `/research/${row.id}/reject`,
    fields: [{ key: "reason", label: t("workflowCommands.formFields.reason"), type: "textarea", required: true }],
    successTitle: t("workflowCommands.researchRejected"),
    errorTitle: t("workflowCommands.failedToRejectResearch"),
    body: (_actorId, payload) => ({ reason: payload.reason }),
  },
  {
    key: "tests.complete",
    label: "RES",
    title: t("workflowCommands.completeTest"),
    icon: "i-lucide-check",
    color: "success",
    selection: { label: t("workflowCommands.completeTest_selection"), color: "success" },
    resource: "tests",
    action: "complete",
    statuses: ["in_progress"],
    endpoint: (row) => `/tests/${row.id}/complete`,
    fields: [
      { key: "value", label: t("workflowCommands.formFields.value"), required: true, layout: { span: 6 } },
      { key: "norm", label: t("workflowCommands.formFields.norm"), layout: { span: 6 } },
      { key: "comment", label: t("workflowCommands.formFields.comment"), type: "textarea" },
    ],
    successTitle: t("workflowCommands.testsCompleted"),
    errorTitle: t("workflowCommands.failedToCompleteTests"),
    body: (_actorId, payload) => ({
      value: payload.value,
      norm: payload.norm,
      comment: payload.comment,
    }),
  },
  {
    key: "tests.reject",
    label: "REJ",
    title: t("workflowCommands.rejectTest"),
    icon: "i-lucide-ban",
    color: "error",
    selection: { label: t("workflowCommands.rejectTest_selection"), color: "error" },
    resource: "tests",
    action: "reject",
    statuses: ["in_progress"],
    endpoint: (row) => `/tests/${row.id}/reject`,
    fields: [{ key: "reason", label: t("workflowCommands.formFields.reason"), type: "textarea", required: true }],
    successTitle: t("workflowCommands.testsRejected"),
    errorTitle: t("workflowCommands.failedToRejectTests"),
    body: (_actorId, payload) => ({ reason: payload.reason }),
  },
];
