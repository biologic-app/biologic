export interface AccessItem {
  key: string;
  label: string;
  icon: string;
  to: string;
}

export const accessItems: AccessItem[] = [
  {
    key: "users",
    label: "Пользователи",
    icon: "i-lucide-users",
    to: "/access/users",
  },
  {
    key: "roles",
    label: "Роли и права",
    icon: "i-lucide-shield-check",
    to: "/access/roles",
  },
];
