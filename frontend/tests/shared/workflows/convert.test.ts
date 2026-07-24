import { describe, expect, test } from "bun:test";
import {
  ensureV2,
  screenFields,
  toScreen,
} from "../../../src/modules/workflows/engine/convert";
import { microbiologyStudy } from "../../../src/modules/workflows/data/microbiology-study";
import { patientIntake } from "../../../src/modules/workflows/data/patient-intake";
import { workflowCreation } from "../../../src/modules/workflows/data/workflow-creation";
import type {
  JournalLoopData,
  JournalSchema,
  JournalStepData,
} from "../../../src/modules/workflows/types/journal";

const demos: Array<[string, JournalSchema]> = [
  ["microbiology-study", microbiologyStudy],
  ["patient-intake", patientIntake],
  ["workflow-creation", workflowCreation],
];

function stepLikeData(schema: JournalSchema) {
  return schema.nodes
    .filter((n) => n.type === "step" || n.type === "loop")
    .map((n) => n.data as JournalStepData | JournalLoopData);
}

describe("toScreen (v1 fields[] → грид)", () => {
  test.each(demos)(
    "%s: каждое поле → отдельный ряд с одним блоком span-12, порядок сохранён",
    (_name, schema) => {
      for (const data of stepLikeData(schema)) {
        const screen = toScreen(data);
        // Ряд на поле, детерминированный id ряда/блока из id поля (§7).
        expect(screen.rows).toHaveLength(data.fields.length);
        data.fields.forEach((field, i) => {
          const row = screen.rows[i];
          expect(row.id).toBe(`row-${field.id}`);
          expect(row.blocks).toHaveLength(1);
          const block = row.blocks[0];
          expect(block.kind).toBe("field");
          expect(block.span).toBe(12);
          expect(block.id).toBe(`block-${field.id}`);
          if (block.kind === "field") {
            // Поле переходит 1:1 (тот же объект — типы/options не мутируются).
            expect(block.field).toBe(field);
          }
        });
        expect(screenFields(screen).map((f) => f.id)).toEqual(
          data.fields.map((f) => f.id),
        );
      }
    },
  );

  test("возвращает существующий screen как есть, если узел уже v2", () => {
    const existing = toScreen({
      label: "s",
      fields: [{ id: "a", label: "A", type: "text" }],
    });
    const passthrough = toScreen({ label: "s", fields: [], screen: existing });
    expect(passthrough).toBe(existing);
  });
});

describe("ensureV2", () => {
  test.each(demos)(
    "%s: step/loop получают screen; formatVersion=2; рёбра/условия не тронуты",
    (_name, schema) => {
      const v2 = ensureV2(schema);
      expect(v2.formatVersion).toBe(2);
      // Рёбра и порядок узлов идентичны.
      expect(v2.edges).toEqual(schema.edges);
      expect(v2.nodes.map((n) => n.id)).toEqual(schema.nodes.map((n) => n.id));

      schema.nodes.forEach((orig, i) => {
        const out = v2.nodes[i];
        expect(out.type).toBe(orig.type);
        if (orig.type === "step" || orig.type === "loop") {
          const data = out.data as JournalStepData | JournalLoopData;
          expect(data.screen).toBeDefined();
          expect(screenFields(data.screen!).map((f) => f.id)).toEqual(
            (orig.data as JournalStepData | JournalLoopData).fields.map(
              (f) => f.id,
            ),
          );
        } else {
          // start/condition/end — data не меняется (условия json-logic сохранены).
          expect(out.data).toEqual(orig.data);
        }
      });
    },
  );

  test.each(demos)("%s: исходная схема не мутируется", (_name, schema) => {
    ensureV2(schema);
    expect(schema.formatVersion).toBeUndefined();
    for (const data of stepLikeData(schema)) {
      expect(data.screen).toBeUndefined();
    }
  });

  test.each(demos)(
    "%s: идемпотентна (повторный вызов на v2 ничего не меняет)",
    (_name, schema) => {
      const once = ensureV2(schema);
      const twice = ensureV2(once);
      expect(twice).toEqual(once);
    },
  );
});
