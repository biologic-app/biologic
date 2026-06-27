import type { UserModeId } from "@/shared/config/user-modes";

export const roleCredentials: Record<UserModeId, { username: string; password: string }> = {
  developer:          { username: "tminww",       password: "tminww123" },
  user_admin:         { username: "admin",         password: "admin123" },
  registrar:          { username: "registrator",   password: "registrator123" },
  sanitary_inspector: { username: "sandoctor",     password: "sandoctor123" },
  lab_doctor:         { username: "doctor",        password: "doctor123" },
  lab_assistant:      { username: "laborant",      password: "laborant123" },
  lab_chief:          { username: "nachlab",       password: "nachlab123" },
  branch_chief:       { username: "nachfil",       password: "nachfil123" },
};
