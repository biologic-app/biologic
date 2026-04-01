import { useAuth } from "@/modules/auth";
import type { Action, Resource } from "@/shared/types/permissions";

export const usePermission = () => {
  const auth = useAuth();

  const can = (resource: Resource, action: Action) =>
    auth.can(resource, action);

  return { can };
};
