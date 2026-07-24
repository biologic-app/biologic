import { describe, expect, test } from "bun:test";
import { useJournalEngine } from "../../../src/modules/workflows/composables/useJournalEngine";
import { microbiologyStudy } from "../../../src/modules/workflows/data/microbiology-study";

// Паритет «Микробиология» (schema-doc §8.3): та же v1-схема, пропущенная через
// ensureV2, обходится движком с тем же результатом (узлы, ветвление, циклы),
// а поля берутся из грид-экрана (currentScreen), не из плоского fields[].

function fieldIds(engine: ReturnType<typeof useJournalEngine>): string[] {
  return engine.currentFields.value.map((f) => f.id);
}

describe("microbiology parity через ensureV2 + currentScreen", () => {
  test("экран первого шага строится из fields (span-12 field-блоки)", () => {
    const engine = useJournalEngine(microbiologyStudy);
    expect(engine.currentStep.value.id).toBe("posev");
    // currentScreen наполнен полями шага в исходном порядке.
    const screenFieldIds = engine.currentScreen.value.rows.flatMap((row) =>
      row.blocks
        .filter((b) => b.kind === "field")
        .map((b) => (b.kind === "field" ? b.field.id : "")),
    );
    expect(screenFieldIds).toEqual([
      "sourceType",
      "sampleNumber",
      "seedingDate",
      "media",
    ]);
    expect(engine.currentScreen.value.rows.every((r) => r.blocks[0].span === 12)).toBe(
      true,
    );
  });

  test("ветка «бульон плюсанул» → пересев → возбудитель найден → цикл → несоответствие", () => {
    const engine = useJournalEngine(microbiologyStudy);

    // posev — обязательные поля не заполнены → дальше нельзя.
    expect(engine.canGoNext.value).toBe(false);
    Object.assign(engine.answers.value, {
      sourceType: "products",
      sampleNumber: "47",
      seedingDate: "2026-07-22",
      media: "broth",
    });
    expect(engine.canGoNext.value).toBe(true);
    engine.goNext();
    expect(engine.currentStep.value.id).toBe("bouillonControl");
    expect(fieldIds(engine)).toEqual(["bouillonTurbid"]);

    // Бульон плюсанул → condition needsReseed = true → reseed.
    engine.answers.value.bouillonTurbid = true;
    engine.goNext();
    expect(engine.currentStep.value.id).toBe("reseed");

    Object.assign(engine.answers.value, {
      reseedDate: "2026-07-23",
      reseedMedia: "чашка №2",
    });
    engine.goNext();
    expect(engine.currentStep.value.id).toBe("identification");

    // Возбудитель найден (organismName заполнен) → condition isPathogenFound = true.
    Object.assign(engine.answers.value, {
      smearResult: "cocci",
      organismName: "Salmonella",
    });
    engine.goNext();
    expect(engine.currentStep.value.id).toBe("additionalTests");
    expect(engine.currentLoop.value).not.toBeNull();

    // Цикл: добавляем одну итерацию, затем выходим.
    Object.assign(engine.answers.value, {
      extraTestName: "оксидаза",
      extraTestResult: "положительно",
    });
    expect(engine.canAddLoopItem.value).toBe(true);
    engine.addLoopItem();
    expect(engine.loopItems.value).toHaveLength(1);
    // Из цикла выйти можно всегда.
    expect(engine.canGoNext.value).toBe(true);
    engine.goNext();
    expect(engine.currentStep.value.id).toBe("conclusionNonCompliant");

    Object.assign(engine.answers.value, {
      complianceStatus: "non_compliant",
      comment: "обнаружен возбудитель",
    });
    engine.goNext();
    expect(engine.isFinished.value).toBe(true);
    expect(engine.loops.value.additionalTests).toHaveLength(1);
  });

  test("ветка «бульон не плюсанул» уходит сразу к заключению-норме", () => {
    const engine = useJournalEngine(microbiologyStudy);
    Object.assign(engine.answers.value, {
      sourceType: "water_objects",
      sampleNumber: "12",
      seedingDate: "2026-07-22",
      media: "plates",
    });
    engine.goNext();
    expect(engine.currentStep.value.id).toBe("bouillonControl");

    engine.answers.value.bouillonTurbid = false;
    engine.goNext();
    // condition needsReseed = false → conclusionNormal напрямую.
    expect(engine.currentStep.value.id).toBe("conclusionNormal");
  });

  test("goBack восстанавливает предыдущий шаг из history", () => {
    const engine = useJournalEngine(microbiologyStudy);
    Object.assign(engine.answers.value, {
      sourceType: "products",
      sampleNumber: "1",
      seedingDate: "2026-07-22",
      media: "broth",
    });
    engine.goNext();
    expect(engine.currentStep.value.id).toBe("bouillonControl");
    engine.goBack();
    expect(engine.currentStep.value.id).toBe("posev");
  });
});
