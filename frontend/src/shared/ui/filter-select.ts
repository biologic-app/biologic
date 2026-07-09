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
