import { apiRequest } from "@/shared/api/client.api";
import { commandActions, crudActions } from "@/shared/constants/permissions";
import type { NamedRef } from "@/shared/types/api";
import type { Action, Permission, Resource } from "@/shared/types/permissions";
import type { AuthUser } from "@/shared/types/auth";

export interface AuthResponse {
  user: AuthUser;
  permissions: Permission[];
  accessExpiresAt: string | null;
  refreshExpiresAt: string | null;
}

interface BackendAuthEnvelope {
  data: {
    user: {
      id: string;
      username: string;
      role_key: string;
      role_name: string;
      status?: string;
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
  // `roles` is the canonical backend resource. `user-types` remains in the
  // union temporarily so older screens can be upgraded independently.
  "roles",
];

const knownActions: Action[] = [...crudActions, ...commandActions, "read", "update"];

const mapResource = (resource: string): Resource | null => {
  const normalized = resource.trim().toLowerCase().replace(/_/g, "-");
  return knownResources.includes(normalized as Resource)
    ? (normalized as Resource)
    : null;
};

const mapAction = (action: string): Action | null => {
  const normalized = action.trim().toLowerCase();
  return knownActions.includes(normalized as Action) ? (normalized as Action) : null;
};

const mapPermissions = (
  permissions: Array<{ resource: string; action: string; scope?: string | null }>,
): Permission[] => {
  const normalized = new Map<string, Permission>();

  permissions.forEach((permission) => {
    const resource = mapResource(permission.resource);
    const action = mapAction(permission.action);
    if (!resource || !action) {
      return;
    }
    normalized.set(`${resource}:${action}`, {
      resource,
      action,
      ...(permission.scope ? { scope: permission.scope as Permission["scope"] } : {}),
    });
  });

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
    status: payload.status ?? "active",
    department: { id: null, name: null } satisfies NamedRef,
    deletedAt: null,
  };
};

const mapSession = (payload: BackendAuthEnvelope["data"]): AuthResponse => ({
  user: mapUser(payload.user),
  permissions: mapPermissions(payload.permissions || []),
  accessExpiresAt: payload.access_expires_at ?? null,
  refreshExpiresAt: payload.refresh_expires_at ?? null,
});

interface BackendPermissionsEnvelope {
  data: {
    permissions: Array<{ resource: string; action: string; scope?: string | null }>;
  };
}

export const login = async (
  loginValue: string,
  password: string,
  rememberMe = false,
) => {
  const response = await apiRequest<BackendAuthEnvelope>("/auth/login", {
    method: "POST",
    body: { username: loginValue, password, rememberMe },
  });
  return mapSession(response.data);
};

export const refresh = async () => {
  const response = await apiRequest<BackendAuthEnvelope>("/auth/refresh", {
    method: "POST",
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
  }).catch(() => null);

  return {
    ...session,
    permissions: permissionsResponse
      ? mapPermissions(permissionsResponse.data.permissions || [])
      : session.permissions,
  };
};
