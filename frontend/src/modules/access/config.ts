import { i18n } from "@/shared/i18n";

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString();

export interface AccessItem {
  key: string;
  label: string;
  icon: string;
  to: string;
}

export const accessItems: AccessItem[] = [
  {
    key: "users",
    label: t("access.users"),
    icon: "i-lucide-users",
    to: "/access/users",
  },
  {
    key: "roles",
    label: t("access.roles"),
    icon: "i-lucide-shield-check",
    to: "/access/roles",
  },
  {
    key: "subscriptions",
    label: "Подписки по ролям",
    icon: "i-lucide-bell-plus",
    to: "/access/subscriptions",
  },
];
