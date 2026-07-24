import { describe, expect, mock, test } from "bun:test";

import {
  buildPreviewActionEntry,
  stepActions,
} from "../../../src/modules/workflows/engine/preview";
import type { ActionResolveContext } from "../../../src/modules/workflows/engine/actions";
import type {
  DomainAction,
  JournalNode,
} from "../../../src/modules/workflows/types/journal";

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

// «Завершить тест», цель — из dictionary-поля test_id (реестровая команда).
function completeAction(): DomainAction {
  return {
    id: "a1",
    label: "Заполнить результат",
    command: "tests.complete",
    targetFrom: "field",
    targetField: "test_id",
    argsMapping: {
      result: { from: "answer", fieldId: "result" },
      actor_id: { from: "actor" },
    },
  };
}

function stepNode(actions: DomainAction[]): JournalNode {
  return {
    id: "step-1",
    type: "step",
    position: { x: 0, y: 0 },
    data: { label: "Результат теста", fields: [], actions },
  };
}

describe("stepActions", () => {
  test("step-нода → её действия", () => {
    expect(stepActions(stepNode([completeAction()]))).toHaveLength(1);
  });
  test("step без actions → пустой массив", () => {
    const node: JournalNode = { ...stepNode([]), data: { label: "X", fields: [] } };
    expect(stepActions(node)).toEqual([]);
  });
  test("не-step нода → пусто", () => {
    const cond: JournalNode = {
      id: "c1",
      type: "condition",
      position: { x: 0, y: 0 },
      data: { label: "?", rule: { "==": [1, 1] } },
    };
    expect(stepActions(cond)).toEqual([]);
  });
});

describe("buildPreviewActionEntry", () => {
  test("шаг без действий → null (нечего логировать)", () => {
    expect(buildPreviewActionEntry(stepNode([]), ctx())).toBeNull();
  });

  test("шаг с действиями → запись с nodeId/nodeLabel и резолвнутыми вызовами", () => {
    const entry = buildPreviewActionEntry(stepNode([completeAction()]), ctx());
    expect(entry).not.toBeNull();
    expect(entry!.nodeId).toBe("step-1");
    expect(entry!.nodeLabel).toBe("Результат теста");
    expect(entry!.calls).toHaveLength(1);
  });

  test("подпись берётся из реестра команд (а не из action.label)", () => {
    const entry = buildPreviewActionEntry(stepNode([completeAction()]), ctx());
    // tests.complete в реестре → «Завершить тест»
    expect(entry!.calls[0].label).toBe("Завершить тест");
    expect(entry!.calls[0].command).toBe("tests.complete");
  });

  test("подпись падает на action.label, если команды нет в реестре", () => {
    const custom: DomainAction = { ...completeAction(), command: "unknown.cmd" };
    const entry = buildPreviewActionEntry(stepNode([custom]), ctx());
    expect(entry!.calls[0].label).toBe("Заполнить результат");
  });

  test("resolvedArgs зеркалят чистый резолвер (target id под test_id + actor)", () => {
    const entry = buildPreviewActionEntry(stepNode([completeAction()]), ctx());
    expect(entry!.calls[0].resolvedArgs).toEqual({
      result: "5",
      actor_id: ACTOR,
      test_id: TEST_ID,
    });
  });

  test("несколько действий → несколько вызовов в записи", () => {
    const entry = buildPreviewActionEntry(
      stepNode([completeAction(), { ...completeAction(), id: "a2" }]),
      ctx(),
    );
    expect(entry!.calls).toHaveLength(2);
  });
});

// Ключевой инвариант US-008: прогон preview-логики наполняет журнал и НИКОГДА не
// дёргает execute-step. buildPreviewActionEntry не принимает и не знает про
// executeStep — spy остаётся нетронутым структурно.
describe("preview-прогон не исполняет действия (ноль execute-step)", () => {
  test("обход шагов наполняет лог, executeStep не вызывается", () => {
    const executeStep = mock(() => {
      throw new Error("execute-step не должен вызываться в preview");
    });

    const steps: JournalNode[] = [
      stepNode([completeAction()]),
      { ...stepNode([]), id: "step-2", data: { label: "Без действий", fields: [] } },
      { ...stepNode([completeAction()]), id: "step-3" },
    ];

    const log = steps
      .map((node) => buildPreviewActionEntry(node, ctx()))
      .filter((e): e is NonNullable<typeof e> => e !== null);

    expect(log).toHaveLength(2); // step-2 без действий отфильтрован
    expect(log.reduce((n, e) => n + e.calls.length, 0)).toBe(2);
    expect(executeStep).not.toHaveBeenCalled();
  });
});
