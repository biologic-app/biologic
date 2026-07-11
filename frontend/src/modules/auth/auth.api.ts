import { apiRequest } from "@/shared/api/client.api";
import { commandActions, crudActions } from "@/shared/constants/permissions";
import type { NamedRef } from "@/shared/types/api";
import type { Action, Permission, Resource } from "@/shared/types/permissions";
import type { AuthUser } from "@/shared/types/auth";

export interface AuthResponse {
  user: AuthUser;
  permissions: Permission[];
}

interface BackendAuthEnvelope {
  data: {
    user: {
      id: string;
      username: string;
      role_key: string;
      role_name: string;
      first_name: string | null;
      last_name: string | null;
      patronymic: string | null;
    };
    permissions: Array<{ resource: string; action: string; scope?: string | null }>;
    access_expires_at: string;
    refresh_expires_at: string | null;
  };
}

const knownResources: Resource[] = [
  "dashboard",
  "directions",
  "research",
  "samples",
  "sample-targets",
  "protocols",
  "results",
  "conclusions",
  "tests",
  "doctors",
  "branches",
  "labs",
  "users",
  "research-goals",
  "sample-types",
  "indicators",
  "protocol-types",
  "statuses",
  "user-types",
  "objects",
];

const knownActions: Action[] = [...crudActions, ...commandActions];

const mapResource = (resource: string): Resource | null => {
  const normalized = resource.trim().toLowerCase().replace(/_/g, "-");
  const mapped =
    normalized === "roles" ||
      normalized === "role-permissions" ||
      normalized === "role-subscription-rules"
      ? "user-types"
      : normalized === "results"
        ? "research"
      : normalized === "direction-statuses" ||
          normalized === "sample-statuses" ||
          normalized === "research-statuses" ||
          normalized === "test-statuses" ||
          normalized === "conclusion-statuses"
        ? "statuses"
      : normalized;
  return knownResources.includes(mapped as Resource)
    ? (mapped as Resource)
    : null;
};

const mapAction = (action: string): Action | null => {
  const normalized = action.trim().toLowerCase();
  const actionMap: Record<string, Action> = {
    read: "view",
    update: "edit",
    issue: "release",
    result: "complete",
  };
  const mapped = actionMap[normalized] ?? normalized;
  return knownActions.includes(mapped as Action) ? (mapped as Action) : null;
};

const mapPermissions = (
  permissions: Array<{ resource: string; action: string }>,
): Permission[] => {
  const normalized = new Map<string, Permission>();

  permissions.forEach((permission) => {
    const resource = mapResource(permission.resource);
    const action = mapAction(permission.action);
    if (!resource || !action) {
      return;
    }
    normalized.set(`${resource}:${action}`, { resource, action });
  });

  if (!normalized.has("dashboard:view")) {
    normalized.set("dashboard:view", { resource: "dashboard", action: "view" });
  }

  return Array.from(normalized.values());
};

const mapUser = (payload: BackendAuthEnvelope["data"]["user"]): AuthUser => {
  const fullName = [payload.last_name,payload.first_name, payload.patronymic]
    .filter(Boolean)
    .join(" ")
    .trim();

  return {
    id: payload.id,
    login: payload.username,
    email: `${payload.username}@local`,
    fullName: fullName || payload.username,
    role: payload.role_key,
    status: "active",
    department: { id: null, name: null } satisfies NamedRef,
    deletedAt: null,
  };
};

const mapSession = (payload: BackendAuthEnvelope["data"]): AuthResponse => ({
  user: mapUser(payload.user),
  permissions: mapPermissions(payload.permissions || []),
});

interface BackendPermissionsEnvelope {
  data: {
    permissions: Array<{ resource: string; action: string; scope?: string | null }>;
  };
}

export const login = async (loginValue: string, password: string) => {
  const response = await apiRequest<BackendAuthEnvelope>("/auth/login", {
    method: "POST",
    body: { username: loginValue, password },
  });
  return mapSession(response.data);
};

export const logout = async () => {
  await apiRequest<{ meta: unknown }>("/auth/logout", { method: "POST" });
};

export const me = async () => {
  const response = await apiRequest<BackendAuthEnvelope>("/auth/me", {
    method: "GET",
  });
  const session = mapSession(response.data);
  const permissionsResponse = await apiRequest<BackendPermissionsEnvelope>("/user/me/permissions", {
    method: "GET",
    headers: { "X-Actor-Id": session.user.id },
  }).catch(() => null);

  return {
    ...session,
    permissions: permissionsResponse
      ? mapPermissions(permissionsResponse.data.permissions || [])
      : session.permissions,
  };
};
