import { computed } from "vue";
import { useStorage } from "@vueuse/core";
import {
  defaultWorkflowRoleKey,
  getWorkflowRole,
  roleWorkspaceModes,
  workflowEntityActions,
  workflowRoles,
  workflowScreens,
  type WorkflowRoleKey,
} from "@/modules/workflows/data";

export function useWorkflowRole() {
  const selectedRoleKey = useStorage<WorkflowRoleKey>(
    "bio-workflow-role",
    defaultWorkflowRoleKey,
  );

  const selectedRole = computed(() => getWorkflowRole(selectedRoleKey.value));
  const selectedMode = computed(() => roleWorkspaceModes[selectedRoleKey.value]);
  const selectedScreens = computed(() =>
    workflowScreens.filter((screen) => screen.roles.includes(selectedRoleKey.value)),
  );
  const selectedEntityActions = computed(() =>
    workflowEntityActions.filter((action) => action.roles.includes(selectedRoleKey.value)),
  );
  const roleItems = workflowRoles.map((role) => ({
    label: `${role.shortName} · ${role.title}`,
    value: role.key,
  }));

  return {
    roleItems,
    selectedEntityActions,
    selectedMode,
    selectedRole,
    selectedRoleKey,
    selectedScreens,
  };
}
