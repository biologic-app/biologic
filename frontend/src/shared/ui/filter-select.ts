type FilterSelectScalarValue = string | number | boolean | null | undefined;
type FilterSelectValue = FilterSelectScalarValue | FilterSelectScalarValue[];

export const filterSelectOverlayUi = {
  content: "z-[80]",
  viewport: "max-h-64 overflow-y-auto",
} as const;

const getFirstSelectedValue = (value: FilterSelectValue) =>
  Array.isArray(value)
    ? value.find((item) => item !== null && item !== undefined && item !== "")
    : value;

export const getFilterSelectModelValue = (value: FilterSelectValue) => {
  const selectedValue = getFirstSelectedValue(value);
  return selectedValue === null || selectedValue === undefined || selectedValue === ""
    ? undefined
    : selectedValue;
};

export const normalizeFilterSelectValue = (value: FilterSelectValue) =>
  getFilterSelectModelValue(value) ?? "";

type FilterSelectResolvedValue = string | number | boolean;

const toSelectedArray = (value: FilterSelectValue): FilterSelectResolvedValue[] =>
  (Array.isArray(value) ? value : [value]).filter(
    (item): item is FilterSelectResolvedValue =>
      item !== null && item !== undefined && item !== "",
  );

// Multi-select variants: the filter value is an array of selected scalars
// (e.g. several status_id UUIDs). buildParams sends it as an IN-list.
export const getFilterMultiSelectModelValue = (
  value: FilterSelectValue,
): FilterSelectResolvedValue[] => toSelectedArray(value);

export const normalizeFilterMultiSelectValue = (
  value: FilterSelectValue,
): FilterSelectResolvedValue[] => toSelectedArray(value);
