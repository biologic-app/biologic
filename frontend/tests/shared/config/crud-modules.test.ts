import { describe, expect, test } from "bun:test";
import {
  crudModules,
  getCrudModuleFilterFields,
} from "../../../src/shared/config/crud-modules";

const expectedFilterFields: Record<string, string[]> = {
  directions: [
    "year_no",
    "base_no",
    "doctor_id",
    "object_id",
    "status_id",
    "is_done",
    "is_urgent",
    "sampled_at",
    "received_at",
    "completed_at",
  ],
  samples: [
    "month_no",
    "name",
    "alternate_name",
    "nomenclature_code",
    "batch_code",
    "supplier",
    "sample_type_id",
    "direction_id",
    "status_id",
    "protocol_id",
    "is_urgent",
    "is_done",
    "sampled_at",
    "received_at",
    "completed_at",
    "deadline",
  ],
  research: [
    "sample_id",
    "research_goal_id",
    "lab_id",
    "status_id",
    "received_at",
    "completed_at",
  ],
  tests: [
    "research_id",
    "indicator_id",
    "status_id",
    "value",
    "norm",
    "comment",
    "is_active",
  ],
};

describe("workflow CRUD filters", () => {
  test.each(Object.entries(expectedFilterFields))(
    "%s exposes every configured filter with an initial state",
    (moduleKey, fields) => {
      const config = crudModules[moduleKey];
      const filterFields = config.filterFields?.map((field) => field.field);

      expect(filterFields).toEqual(fields);
      fields.forEach((field) => {
        expect(config.initialFilters[field]).toBeDefined();
      });
    },
  );

  test("does not expose audit timestamps as filters", () => {
    Object.values(crudModules).forEach((config) => {
      const fieldNames = getCrudModuleFilterFields(config).map((field) => field.field);

      expect(fieldNames).not.toContain("created_at");
      expect(fieldNames).not.toContain("updated_at");
    });
  });

  test("uses dropdown filters for reference fields", () => {
    const referenceFields = [
      crudModules.directions.filterFields?.find((field) => field.field === "doctor_id"),
      crudModules.directions.filterFields?.find((field) => field.field === "object_id"),
      crudModules.samples.filterFields?.find((field) => field.field === "sample_type_id"),
      crudModules.research.filterFields?.find((field) => field.field === "research_goal_id"),
      crudModules.tests.filterFields?.find((field) => field.field === "indicator_id"),
      getCrudModuleFilterFields(crudModules.objects).find((field) => field.field === "branch_id"),
    ];

    referenceFields.forEach((field) => {
      expect(field?.filter?.type).toBe("select");
      expect(field?.filter?.source).toBeTruthy();
    });
  });

  test("does not configure workflow dropdown filters as multi-select", () => {
    ["directions", "samples", "research", "tests"].forEach((moduleKey) => {
      const config = crudModules[moduleKey];

      getCrudModuleFilterFields(config).forEach((field) => {
        expect(field.filter?.type).not.toBe("multiSelect");
      });
    });
  });
});
