import { i18n } from "@/shared/i18n";

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString();

type PlainObject = Record<string, unknown>;

const compact = (items: Array<string | number | null | undefined | false>) =>
  items
    .map((item) => item === null || item === undefined || item === false ? "" : String(item).trim())
    .filter(Boolean);

const toOptionValue = (value: unknown) =>
  typeof value === "string"
  || typeof value === "number"
  || typeof value === "boolean"
  || value === null
    ? value
    : String(value ?? "");

const formatShortId = (value: unknown) => {
  if (typeof value !== "string" && typeof value !== "number") {
    return t("referenceOptions.recordFallback");
  }

  const text = String(value);
  const uuidPrefix = text.match(/^[0-9a-f]{8}/i)?.[0];
  return (uuidPrefix ?? text.slice(0, 8)).toUpperCase();
};

const isStatusReferencePath = (path: string) => {
  const normalizedPath = path.toLowerCase().split("?")[0]?.replace(/\/+$/, "") ?? "";
  return normalizedPath === "/statuses" || normalizedPath.endsWith("_statuses");
};

const isObjectReferencePath = (path: string) => {
  const normalizedPath = path.toLowerCase().split("?")[0]?.replace(/\/+$/, "") ?? "";
  return normalizedPath === "/objects";
};

const isSampleTypeReferencePath = (path: string) => {
  const normalizedPath = path.toLowerCase().split("?")[0]?.replace(/\/+$/, "") ?? "";
  return normalizedPath === "/sample_types";
};

const formatReferenceLabel = (row: PlainObject, path: string) => {
  if ((isStatusReferencePath(path) || isObjectReferencePath(path) || isSampleTypeReferencePath(path)) && row.name) {
    return String(row.name);
  }

  if (row.name && row.code) {
    return `${String(row.name)} (${String(row.code)})`;
  }

  if (row.name || row.full_name || row.code) {
    return String(row.name || row.full_name || row.code);
  }

  const personName = compact([row.last_name as string, row.first_name as string, row.patronymic as string]).join(" ");
  if (personName) {
    return personName;
  }

  if (row.base_no !== null && row.base_no !== undefined && row.base_no !== "") {
    return row.year_no ? `№ ${row.year_no}-${row.base_no}` : `№ ${row.base_no}`;
  }

  const researchParts = compact([
    row.sample_id ? t("referenceOptions.sample", { code: formatShortId(row.sample_id) }) : null,
    row.research_goal_id ? t("referenceOptions.goal", { code: formatShortId(row.research_goal_id) }) : null,
  ]);
  if (researchParts.length) {
    return t("referenceOptions.researchLabel", { parts: researchParts.join(", ") });
  }

  return t("crud.recordCode", { code: formatShortId(row.id) });
};

export const formatReferenceOption = (row: PlainObject, path: string) => ({
  label: formatReferenceLabel(row, path),
  value: toOptionValue(row.id),
});
