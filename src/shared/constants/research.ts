import type { ResearchStatus, ResearchTest } from "@/shared/types";

export const statusColors: Record<ResearchStatus, "neutral" | "primary" | "info" | "success" | "error"> = {
  registered: "neutral",
  inProgress: "primary",
  review: "info",
  completed: "success",
  rejected: "error",
};

export const statusIcons: Record<ResearchStatus, string> = {
  registered: "i-lucide-clipboard-check",
  inProgress: "i-lucide-flask-conical",
  review: "i-lucide-search-check",
  completed: "i-lucide-circle-check",
  rejected: "i-lucide-circle-x",
};

export const interpretationColors: Record<ResearchTest["interpretation"], "neutral" | "success" | "warning" | "error"> = {
  normal: "success",
  warning: "warning",
  critical: "error",
  pending: "neutral",
};

export const interpretationLabels: Record<ResearchTest["interpretation"], string> = {
  normal: "Норма",
  warning: "Отклонение",
  critical: "Критично",
  pending: "Ожидается",
};
