type BadgeColor = "neutral" | "primary" | "info" | "success" | "warning" | "error";

const STATUS_COLORS: Record<string, BadgeColor> = {
  draft: "neutral",
  pending: "warning",
  registered: "info",
  in_progress: "info",
  analyzed: "info",
  completed: "success",
  partially_completed: "success",
  rejected: "error",
};

const LABEL_PATTERNS: Array<[RegExp, string]> = [
  [/draft|чернов/i, "draft"],
  [/pending|регистрац/i, "pending"],
  [/registered|зарегистр/i, "registered"],
  [/in_progress|работ|исслед/i, "in_progress"],
  [/rejected|отклон|брак/i, "rejected"],
  [/partially/i, "partially_completed"],
  [/completed|заверш/i, "completed"],
  [/analyzed|анализ/i, "analyzed"],
];

export const resolveStatusCode = (code: string): string => {
  if (STATUS_COLORS[code] !== undefined) return code;
  const match = LABEL_PATTERNS.find(([re]) => re.test(code));
  return match ? match[1] : code;
};

export const getStatusBadgeColor = (code: string): BadgeColor =>
  STATUS_COLORS[resolveStatusCode(code)] ?? "primary";
