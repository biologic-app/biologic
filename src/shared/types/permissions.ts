export type Resource =
  | "dashboard"
  | "directions"
  | "research"
  | "samples"
  | "sample-targets"
  | "protocols"
  | "results"
  | "conclusions"
  | "tests"
  | "doctors"
  | "branches"
  | "labs"
  | "users"
  | "research-goals"
  | "sample-types"
  | "indicators"
  | "protocol-types"
  | "statuses"
  | "user-types"
  | "objects";

export type CrudAction = "view" | "create" | "edit" | "delete";

export type CommandAction =
  | "import"
  | "export"
  | "register"
  | "start"
  | "complete"
  | "release"
  | "reject"
  | "requeue"
  | "approve";

export type Action = CrudAction | CommandAction;

export interface Permission {
  resource: Resource;
  action: Action;
}

export interface PermissionOverride {
  resource: Resource;
  action: Action;
  allowed: boolean;
}

export interface PermissionSummary {
  view: number;
  create: number;
  edit: number;
  delete: number;
}
