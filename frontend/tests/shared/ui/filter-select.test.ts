import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  filterSelectOverlayUi,
  getFilterSelectModelValue,
  normalizeFilterSelectValue,
} from "../../../src/shared/ui/filter-select";

const dictionaryCrudContentSource = readFileSync(
  resolve(import.meta.dir, "../../../src/modules/dictionaries/pages/DictionaryCrudContent.vue"),
  "utf8",
);
const workflowPageSources = [
  "DirectionsPage.vue",
  "SamplesPage.vue",
  "ResearchPage.vue",
  "TestsPage.vue",
].map((file) =>
  readFileSync(resolve(import.meta.dir, "../../../src/pages", file), "utf8"),
);

// Все workflow-страницы переведены на WorkflowCrudPage — он единственный
// владелец локального состояния фильтра (открытие фильтра без дочерних ref).
const filterStateOwnerSources = [
  resolve(import.meta.dir, "../../../src/shared/ui/WorkflowCrudPage.vue"),
].map((path) => readFileSync(path, "utf8"));

const dictionaryCrudMountedHook =
  dictionaryCrudContentSource.match(/onMounted\(async \(\) => \{([\s\S]*?)\n\}\);/)?.[1] ?? "";

describe("filter select model helpers", () => {
  test.each([
    [false, false],
    [0, 0],
    [[true, false], true],
    [["", "abc"], "abc"],
    [[], undefined],
    ["", undefined],
    [null, undefined],
    [undefined, undefined],
  ])("maps stored value %p to SelectMenu model %p", (value, expected) => {
    expect(getFilterSelectModelValue(value)).toBe(expected);
  });

  test.each([
    [false, false],
    [0, 0],
    ["abc", "abc"],
    [[false], false],
    [[], ""],
    [null, ""],
    [undefined, ""],
  ])("maps SelectMenu event %p to stored filter value %p", (value, expected) => {
    expect(normalizeFilterSelectValue(value)).toBe(expected);
  });

  test("keeps dropdown content above sibling filter controls", () => {
    expect(filterSelectOverlayUi.content).toContain("z-[80]");
    expect(filterSelectOverlayUi.viewport).toContain("overflow-y-auto");
  });

  test("uses a basic select menu without lazy scroll loading", () => {
    expect(dictionaryCrudContentSource).not.toContain("useInfiniteScroll");
    expect(dictionaryCrudContentSource).not.toContain("loadReferenceOptionsPage");
    expect(dictionaryCrudContentSource).not.toContain("loadMoreFilterOptions");
    expect(dictionaryCrudContentSource).not.toContain("bindFilterSelectRef");
    expect(dictionaryCrudContentSource).not.toContain("onFilterSelectOpen");
    expect(dictionaryCrudContentSource).not.toContain(":virtualize");
  });

  test("does not preload form or filter reference options during page mount", () => {
    expect(dictionaryCrudMountedHook).toContain("table.fetch()");
    expect(dictionaryCrudMountedHook).not.toContain("loadFilterReferenceOptions");
    expect(dictionaryCrudMountedHook).not.toContain("loadFormReferenceOptions");
  });

  test("workflow pages open filters from local state instead of waiting for child refs", () => {
    filterStateOwnerSources.forEach((source) => {
      expect(source).toContain("const filterModalOpen = ref");
      expect(source).toContain("@open=\"filterModalOpen = true\"");
      expect(source).toContain("v-model:filter-open=\"filterModalOpen\"");
    });

    // Ни одна страница не должна открывать фильтр мутацией ref дочернего компонента.
    workflowPageSources.forEach((source) => {
      expect(source).not.toContain("crudContent!.filterModalOpen = true");
    });
  });

  test("binds :multiple on filter selects only for multiSelect filters", () => {
    expect(dictionaryCrudContentSource).toContain(
      ":multiple=\"filterField.filter?.type === 'multiSelect'\"",
    );
  });
});
