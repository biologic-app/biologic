export const borderedCrudTableUi = {
  root: "rounded-lg border border-default bg-default",
  base: "border-separate border-spacing-0",
  thead: "[&>tr]:bg-elevated/50 [&>tr]:after:content-none",
  tbody: "[&>tr]:last:[&>td]:border-b-0",
  th: "border-r border-b border-default px-6 py-1.5 text-left text-sm font-semibold text-highlighted last:border-r-0",
  td: "border-r border-b border-default px-6 py-1.5 text-sm whitespace-nowrap text-muted last:border-r-0",
} as const;
