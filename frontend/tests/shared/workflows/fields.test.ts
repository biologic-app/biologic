import { describe, expect, test } from "bun:test";
import {
  applyComputedFields,
  evaluateComputed,
  fieldsSatisfied,
  isEmpty,
  isFieldSatisfied,
  isVisible,
  maxSizeMb,
  validateField,
} from "../../../src/modules/workflows/engine/fields";
import type {
  JournalAnswers,
  JournalField,
} from "../../../src/modules/workflows/types/journal";

// US-005: чистая логика полей раннера — validation, visibleWhen, computed.

describe("validateField (min/max/regex — schema-doc §4)", () => {
  test("min по числу: значение ниже границы невалидно", () => {
    const field: JournalField = {
      id: "v",
      label: "Значение",
      type: "number",
      validation: [{ kind: "min", value: 10, message: "не меньше 10" }],
    };
    expect(validateField(field, 5)).toBe("не меньше 10");
    expect(validateField(field, 10)).toBeNull();
    expect(validateField(field, 42)).toBeNull();
  });

  test("max по числу: значение выше границы невалидно", () => {
    const field: JournalField = {
      id: "v",
      label: "Значение",
      type: "number",
      validation: [{ kind: "max", value: 100 }],
    };
    expect(validateField(field, 101)).toBe("Максимум 100");
    expect(validateField(field, 100)).toBeNull();
  });

  test("min/max по строке применяются к её длине", () => {
    const field: JournalField = {
      id: "code",
      label: "Код",
      type: "text",
      validation: [
        { kind: "min", value: 3 },
        { kind: "max", value: 5 },
      ],
    };
    expect(validateField(field, "ab")).toBe("Минимум 3"); // длина 2 < 3
    expect(validateField(field, "abc")).toBeNull(); // длина 3
    expect(validateField(field, "abcdef")).toBe("Максимум 5"); // длина 6 > 5
  });

  test("regex: несоответствие паттерну возвращает сообщение", () => {
    const field: JournalField = {
      id: "email",
      label: "Email",
      type: "text",
      validation: [
        { kind: "regex", pattern: "^[^@]+@[^@]+$", message: "нужен email" },
      ],
    };
    expect(validateField(field, "no-at-sign")).toBe("нужен email");
    expect(validateField(field, "user@example.com")).toBeNull();
  });

  test("пустое значение не валидируется (это забота required)", () => {
    const field: JournalField = {
      id: "v",
      label: "Значение",
      type: "number",
      validation: [{ kind: "min", value: 10 }],
    };
    expect(validateField(field, "")).toBeNull();
    expect(validateField(field, null)).toBeNull();
    expect(validateField(field, undefined)).toBeNull();
  });

  test("поле без правил валидно всегда", () => {
    const field: JournalField = { id: "v", label: "V", type: "text" };
    expect(validateField(field, "что угодно")).toBeNull();
  });

  test("maxSizeMb извлекается из правил (file)", () => {
    const field: JournalField = {
      id: "doc",
      label: "Документ",
      type: "file",
      validation: [{ kind: "maxSizeMb", value: 10 }],
    };
    expect(maxSizeMb(field)).toBe(10);
    expect(maxSizeMb({ id: "x", label: "X", type: "file" })).toBeNull();
  });
});

describe("isVisible / required (visibleWhen — schema-doc §4)", () => {
  const hidden: JournalField = {
    id: "reason",
    label: "Причина",
    type: "text",
    required: true,
    // видимо только когда approved === false
    visibleWhen: { "==": [{ var: "approved" }, false] },
  };

  test("visibleWhen управляет видимостью поверх answers", () => {
    expect(isVisible(hidden, { approved: true })).toBe(false);
    expect(isVisible(hidden, { approved: false })).toBe(true);
  });

  test("поле без visibleWhen всегда видимо", () => {
    const field: JournalField = { id: "a", label: "A", type: "text" };
    expect(isVisible(field, {})).toBe(true);
  });

  test("скрытое обязательное поле не блокирует переход (не required)", () => {
    // approved === true → reason скрыто → пустое значение не мешает.
    const answers: JournalAnswers = { approved: true };
    expect(isFieldSatisfied(hidden, answers)).toBe(true);
  });

  test("видимое обязательное пустое поле блокирует переход", () => {
    const answers: JournalAnswers = { approved: false };
    expect(isFieldSatisfied(hidden, answers)).toBe(false);
    answers.reason = "брак";
    expect(isFieldSatisfied(hidden, answers)).toBe(true);
  });

  test("fieldsSatisfied: скрытые поля исключены из required-проверки", () => {
    const visibleReq: JournalField = {
      id: "name",
      label: "Имя",
      type: "text",
      required: true,
    };
    const fields = [visibleReq, hidden];
    // name пусто → блок; reason скрыто (approved true) → не влияет.
    expect(fieldsSatisfied(fields, { approved: true })).toBe(false);
    expect(fieldsSatisfied(fields, { approved: true, name: "Иван" })).toBe(true);
    // reason становится видимым и обязательным → снова блок.
    expect(fieldsSatisfied(fields, { approved: false, name: "Иван" })).toBe(false);
  });
});

describe("isEmpty", () => {
  test("пустые значения", () => {
    expect(isEmpty(undefined)).toBe(true);
    expect(isEmpty(null)).toBe(true);
    expect(isEmpty("")).toBe(true);
    expect(isEmpty([])).toBe(true);
  });
  test("непустые значения", () => {
    expect(isEmpty(0)).toBe(false);
    expect(isEmpty(false)).toBe(false);
    expect(isEmpty("x")).toBe(false);
    expect(isEmpty([1])).toBe(false);
  });
});

describe("computed-поля (jsonLogic поверх answers — schema-doc §4)", () => {
  const total: JournalField = {
    id: "total",
    label: "Итого",
    type: "computed",
    expr: { "+": [{ var: "a" }, { var: "b" }] },
  };

  test("evaluateComputed считает выражение по answers", () => {
    expect(evaluateComputed(total, { a: 2, b: 3 })).toBe(5);
  });

  test("applyComputedFields пишет результат в answers и сообщает об изменении", () => {
    const answers: JournalAnswers = { a: 4, b: 6 };
    const changed = applyComputedFields([total], answers);
    expect(changed).toBe(true);
    expect(answers.total).toBe(10);
  });

  test("повторный вызов без изменений входов ничего не меняет (сходимость)", () => {
    const answers: JournalAnswers = { a: 1, b: 1, total: 2 };
    expect(applyComputedFields([total], answers)).toBe(false);
    expect(answers.total).toBe(2);
  });

  test("computed доступно последующим полям/условиям через answers", () => {
    // total пересчитан → условие поверх него получает свежее значение.
    const answers: JournalAnswers = { a: 7, b: 8 };
    applyComputedFields([total], answers);
    expect(answers.total).toBe(15);
  });

  test("не-computed поля игнорируются", () => {
    const plain: JournalField = { id: "a", label: "A", type: "number" };
    const answers: JournalAnswers = { a: 1 };
    expect(applyComputedFields([plain], answers)).toBe(false);
  });
});
