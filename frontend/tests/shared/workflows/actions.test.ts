import { describe, expect, test } from "bun:test";

import {
  StepAttemptTracker,
  resolveAction,
  resolveActionArgs,
  resolveActions,
  resolveRef,
  resolveTargetId,
} from "../../../src/modules/workflows/engine/actions";
import type {
  ActionResolveContext,
} from "../../../src/modules/workflows/engine/actions";
import type { DomainAction } from "../../../src/modules/workflows/types/journal";

const ACTOR = "11111111-1111-1111-1111-111111111111";
const RESEARCH = "22222222-2222-2222-2222-222222222222";
const TEST_ID = "33333333-3333-3333-3333-333333333333";

function ctx(over: Partial<ActionResolveContext> = {}): ActionResolveContext {
  return {
    answers: { result: "5", verdict: "pass", test_id: TEST_ID },
    actorId: ACTOR,
    scopeId: RESEARCH,
    ...over,
  };
}

// Действие «завершить тест», цель — из dictionary-поля test_id (эталон «Лабораторный»).
function completeFromField(): DomainAction {
  return {
    id: "a1",
    label: "Завершить тест",
    command: "tests.complete",
    targetFrom: "field",
    targetField: "test_id",
    argsMapping: {
      result: { from: "answer", fieldId: "result" },
      verdict: { from: "answer", fieldId: "verdict" },
      actor_id: { from: "actor" },
    },
  };
}

describe("resolveRef", () => {
  test("answer → значение из answers", () => {
    expect(resolveRef({ from: "answer", fieldId: "result" }, ctx())).toBe("5");
  });
  test("const → литерал", () => {
    expect(resolveRef({ from: "const", value: 42 }, ctx())).toBe(42);
  });
  test("actor → actorId контекста", () => {
    expect(resolveRef({ from: "actor" }, ctx())).toBe(ACTOR);
  });
  test("actor при отсутствии → null", () => {
    expect(resolveRef({ from: "actor" }, ctx({ actorId: null }))).toBeNull();
  });
});

describe("resolveTargetId", () => {
  test("targetFrom scope → scopeId", () => {
    const action: DomainAction = { ...completeFromField(), targetFrom: "scope", targetField: undefined };
    expect(resolveTargetId(action, ctx())).toBe(RESEARCH);
  });
  test("targetFrom field → answers[targetField]", () => {
    expect(resolveTargetId(completeFromField(), ctx())).toBe(TEST_ID);
  });
  test("targetFrom field без targetField → undefined", () => {
    const action: DomainAction = { ...completeFromField(), targetField: undefined };
    expect(resolveTargetId(action, ctx())).toBeUndefined();
  });
});

describe("resolveActionArgs", () => {
  test("собирает args + инъектит target id под targetKey реестра (test_id)", () => {
    const args = resolveActionArgs(completeFromField(), ctx());
    expect(args).toEqual({
      result: "5",
      verdict: "pass",
      actor_id: ACTOR,
      test_id: TEST_ID,
    });
  });
  test("пустые (null/undefined) значения опускаются — backend применит фолбэк", () => {
    const action = completeFromField();
    const args = resolveActionArgs(action, ctx({ actorId: null, answers: { result: "5", test_id: TEST_ID } }));
    expect("actor_id" in args).toBe(false); // actor=null опущен
    expect("verdict" in args).toBe(false); // отсутствует в answers → опущен
    expect(args.result).toBe("5");
    expect(args.test_id).toBe(TEST_ID);
  });
  test("явный argsMapping приоритетнее автоинъекции target id", () => {
    const action: DomainAction = {
      ...completeFromField(),
      argsMapping: { ...completeFromField().argsMapping, test_id: { from: "const", value: "explicit" } },
    };
    expect(resolveActionArgs(action, ctx()).test_id).toBe("explicit");
  });
});

describe("resolveAction / resolveActions", () => {
  test("resolveAction возвращает actionId/command/resolvedArgs", () => {
    const r = resolveAction(completeFromField(), ctx());
    expect(r.actionId).toBe("a1");
    expect(r.command).toBe("tests.complete");
    expect(r.resolvedArgs.test_id).toBe(TEST_ID);
  });
  test("resolveActions мапит несколько действий", () => {
    const r = resolveActions([completeFromField(), completeFromField()], ctx());
    expect(r).toHaveLength(2);
  });
});

describe("StepAttemptTracker (attempt-семантика)", () => {
  test("current стабилен (=1) — прозрачный ретрай шлёт ТОТ ЖЕ attempt", () => {
    const t = new StepAttemptTracker();
    expect(t.current("run", "node")).toBe(1);
    expect(t.current("run", "node")).toBe(1); // без изменений между вызовами
  });
  test("nextAttempt инкрементит (осознанный повтор)", () => {
    const t = new StepAttemptTracker();
    expect(t.nextAttempt("run", "node")).toBe(2);
    expect(t.current("run", "node")).toBe(2);
    expect(t.nextAttempt("run", "node")).toBe(3);
  });
  test("попытки изолированы по (run,node)", () => {
    const t = new StepAttemptTracker();
    t.nextAttempt("run", "nodeA");
    expect(t.current("run", "nodeB")).toBe(1);
  });
  test("reset возвращает шаг к первой попытке", () => {
    const t = new StepAttemptTracker();
    t.nextAttempt("run", "node");
    t.reset("run", "node");
    expect(t.current("run", "node")).toBe(1);
  });
});
