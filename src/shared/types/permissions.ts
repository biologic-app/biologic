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

export type AccessScope =
  | "own"
  | "own_lab"
  | "all_labs"
  | "own_branch"
  | "all_branches"
  | "all";

export interface Permission {
  id?: string;
  permission_id?: string;
  resource: Resource;
  action: Action;
  scope?: AccessScope;
}

export interface PermissionOverride {
  permission_id?: string;
  resource: Resource;
  action: Action;
  allowed: boolean;
  scope?: AccessScope | null;
}

export interface PermissionSummary {
  view: number;
  create: number;
  edit: number;
  delete: number;
}
