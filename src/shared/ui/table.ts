import { h } from "vue";

export const borderedCrudTableUi = {
  root: "crud-table-scroll h-full min-h-0 rounded-lg border border-default bg-default overflow-auto",
  base: "border-separate border-spacing-0",
  thead: "[&>tr]:bg-elevated/50 [&>tr]:after:content-none",
  tbody: "[&>tr]:last:[&>td]:border-b-0",
  tr: "h-9 min-h-9 cursor-pointer transition-colors hover:bg-accented/70 data-[selected=true]:bg-primary/10 data-[selected=true]:hover:bg-primary/15 data-[selected=true]:shadow-[inset_4px_0_0_var(--ui-primary)]",
  th: "h-9 border-r border-b border-default px-6 py-0 text-left text-sm font-semibold text-highlighted last:border-r-0",
  td: "h-9 border-r border-b border-default px-6 py-0 text-sm whitespace-nowrap text-muted last:border-r-0",
  empty: "p-0 align-middle",
  loading: "p-0",
} as const;

export type SkeletonTableRow = {
  id: string;
  __skeleton: true;
};

export const createSkeletonRows = <T>(count = 20) =>
  Array.from({ length: count }, (_, index) => ({
    id: `skeleton-${index}`,
    __skeleton: true,
  }) as T & SkeletonTableRow);

export const isSkeletonRow = (row: unknown): row is SkeletonTableRow =>
  typeof row === "object"
  && row !== null
  && (row as Partial<SkeletonTableRow>).__skeleton === true;

export const renderSkeletonCell = (key?: string, index = 0) => {
  const width =
    key === "select"
      ? "w-5"
      : key === "actions"
        ? "ml-auto w-8"
            : index % 3 === 0
              ? "w-2/3"
              : index % 3 === 1
                ? "w-5/6"
                : "w-7/12";

  return h("div", { class: "flex h-9 items-center" }, [
    h("div", {
      class: `h-3.5 ${width} animate-pulse rounded-md bg-elevated`,
      "aria-hidden": "true",
    }),
  ]);
};
