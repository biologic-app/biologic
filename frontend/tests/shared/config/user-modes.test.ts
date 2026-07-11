import { describe, expect, test } from "bun:test";
import {
  isSuperAdminRole,
  modeAllows,
  resolveModePermissions,
  superAdminRoles,
} from "../../../src/shared/config/user-modes";

describe("isSuperAdminRole", () => {
  test("возвращает true для роли developer", () => {
    expect(isSuperAdminRole("developer")).toBe(true);
  });

  test("возвращает false для обычных ролей", () => {
    for (const role of ["registrar", "lab_doctor", "user_admin", "branch_chief"]) {
      expect(isSuperAdminRole(role)).toBe(false);
    }
  });

  test("возвращает false для null/undefined/пустой строки", () => {
    expect(isSuperAdminRole(null)).toBe(false);
    expect(isSuperAdminRole(undefined)).toBe(false);
    expect(isSuperAdminRole("")).toBe(false);
  });

  test("superAdminRoles содержит developer", () => {
    expect(superAdminRoles.has("developer")).toBe(true);
  });
});

describe("developer mode wildcard", () => {
  test("пресет developer разрешает любой ресурс и действие", () => {
    const perms = resolveModePermissions("developer");
    expect(modeAllows(perms, "directions", "release")).toBe(true);
    expect(modeAllows(perms, "conclusions", "approve")).toBe(true);
    expect(modeAllows(perms, "users", "delete")).toBe(true);
  });
});
