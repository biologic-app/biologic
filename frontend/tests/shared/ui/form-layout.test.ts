import { describe, expect, test } from "bun:test";
import { getFormFieldLayoutClass } from "../../../src/shared/ui/form-layout";
import type { FormField } from "../../../src/shared/types/form";

describe("getFormFieldLayoutClass", () => {
  test("uses two fields per row by default", () => {
    expect(getFormFieldLayoutClass({ key: "name", label: "Name" })).toBe("md:col-span-6");
  });

  test("uses full row by default for textarea fields", () => {
    expect(
      getFormFieldLayoutClass({ key: "comment", label: "Comment", type: "textarea" }),
    ).toBe("md:col-span-12");
  });

  test.each([
    [12, "md:col-span-12"],
    [6, "md:col-span-6"],
    [4, "md:col-span-4"],
  ] as Array<[NonNullable<FormField["layout"]>["span"], string]>)(
    "maps explicit span %s to a grid class",
    (span, expectedClass) => {
      expect(
        getFormFieldLayoutClass({
          key: "field",
          label: "Field",
          layout: { span },
        }),
      ).toBe(expectedClass);
    },
  );
});
