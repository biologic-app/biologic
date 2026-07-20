// Canonical lifecycle status codes across entities. Used to decide whether an
// incoming value is already a code or a human label that needs resolving.
const KNOWN_STATUS_CODES = new Set<string>([
  "draft",
  "pending",
  "registered",
  "in_progress",
  "analyzed",
  "completed",
  "partially_completed",
  "rejected",
]);

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

// Normalize a status value (code or human label) to its canonical code, used
// for status-based workflow logic (command availability, delete rules). Colors
// no longer flow through here — those come from the backend `color` field via
// `shared/domain/status-color.ts`.
export const resolveStatusCode = (code: string): string => {
  if (KNOWN_STATUS_CODES.has(code)) return code;
  const match = LABEL_PATTERNS.find(([re]) => re.test(code));
  return match ? match[1] : code;
};
