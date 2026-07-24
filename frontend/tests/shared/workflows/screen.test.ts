import { describe, expect, test } from "bun:test";
import {
  addColumn,
  appendBlockAsRow,
  availableSpan,
  clampSpan,
  createBlock,
  createField,
  insertBlockInRow,
  moveBlockToNewRow,
  moveBlockToRow,
  removeBlock,
  removeColumn,
  rowUsedSpan,
  setSpan,
  PALETTE,
} from "../../../src/modules/workflows/engine/screen";
import type {
  Block,
  Screen,
  TableBlock,
} from "../../../src/modules/workflows/types/journal";

// Мини-грид: два поля span-6 в одном ряду, одно поле span-12 во втором.
function twoSlotScreen(): { screen: Screen; a: Block; b: Block; c: Block } {
  const a: Block = { id: "a", span: 6, kind: "field", field: createField("text") };
  const b: Block = { id: "b", span: 6, kind: "field", field: createField("number") };
  const c: Block = { id: "c", span: 12, kind: "field", field: createField("date") };
  const screen: Screen = {
    rows: [
      { id: "r1", blocks: [a, b] },
      { id: "r2", blocks: [c] },
    ],
  };
  return { screen, a, b, c };
}

describe("span helpers", () => {
  test("clampSpan держит 1..12 и округляет", () => {
    expect(clampSpan(0)).toBe(1);
    expect(clampSpan(99)).toBe(12);
    expect(clampSpan(3.6)).toBe(4);
  });

  test("rowUsedSpan / availableSpan учитывают исключение блока", () => {
    const { screen } = twoSlotScreen();
    const row = screen.rows[0];
    expect(rowUsedSpan(row)).toBe(12);
    expect(availableSpan(row)).toBe(0);
    // Исключив блок a (span 6), свободно 6 колонок.
    expect(availableSpan(row, "a")).toBe(6);
  });
});

describe("resize span (сумма span ряда ≤ 12)", () => {
  test("setSpan клампит к свободному месту ряда", () => {
    const { screen } = twoSlotScreen();
    // В ряду r1 у блока b сосед a занимает 6 → максимум для b это 6.
    setSpan(screen, "b", 10);
    expect(screen.rows[0].blocks.find((x) => x.id === "b")!.span).toBe(6);
  });

  test("setSpan свободно меняет одиночный блок ряда", () => {
    const { screen } = twoSlotScreen();
    setSpan(screen, "c", 4);
    expect(screen.rows[1].blocks[0].span).toBe(4);
  });
});

describe("drag между слотами", () => {
  test("перемещение поля в другой ряд (между слотами)", () => {
    const { screen } = twoSlotScreen();
    // Тащим b из r1 в r2 (одиночный span-12 блок c). Свободного места нет →
    // span клампится к минимуму 1, но блок реально переезжает.
    moveBlockToRow(screen, "b", "r2", 0);
    expect(screen.rows[0].blocks.map((x) => x.id)).toEqual(["a"]);
    expect(screen.rows[1].blocks.map((x) => x.id)).toEqual(["b", "c"]);
  });

  test("перемещение внутри ряда меняет порядок слотов", () => {
    const { screen } = twoSlotScreen();
    // b перед a → порядок [b, a].
    moveBlockToRow(screen, "b", "r1", 0);
    expect(screen.rows[0].blocks.map((x) => x.id)).toEqual(["b", "a"]);
  });

  test("перемещение в новый ряд и очистка опустевшего", () => {
    const { screen } = twoSlotScreen();
    // c был единственным в r2 → r2 опустеет и удалится, c уедет новым рядом в конец.
    moveBlockToNewRow(screen, "c", 2);
    expect(screen.rows).toHaveLength(2);
    expect(screen.rows[0].blocks.map((x) => x.id)).toEqual(["a", "b"]);
    expect(screen.rows[1].blocks.map((x) => x.id)).toEqual(["c"]);
  });
});

describe("вставка из палитры", () => {
  test("insertBlockInRow клампит span к свободному месту", () => {
    const { screen } = twoSlotScreen();
    const field = createBlock(PALETTE[0].items[0], 12); // текстовое поле, span 12
    // r2 занят на 12 (блок c) → места нет → новый блок падает новым рядом после r2.
    insertBlockInRow(screen, "r2", field);
    expect(screen.rows).toHaveLength(3);
    expect(screen.rows[2].blocks[0].id).toBe(field.id);
  });

  test("insertBlockInRow помещает в свободное место с клампом span", () => {
    const screen: Screen = { rows: [{ id: "r1", blocks: [] }] };
    const field = createBlock(PALETTE[0].items[0], 12);
    insertBlockInRow(screen, "r1", field);
    expect(screen.rows[0].blocks).toHaveLength(1);
    expect(screen.rows[0].blocks[0].span).toBe(12);
  });

  test("appendBlockAsRow добавляет новый ряд", () => {
    const { screen } = twoSlotScreen();
    const section = createBlock(PALETTE[2].items[0]);
    appendBlockAsRow(screen, section);
    expect(screen.rows).toHaveLength(3);
    expect(screen.rows[2].blocks[0].kind).toBe("section");
  });
});

describe("удаление", () => {
  test("removeBlock убирает блок и чистит пустой ряд", () => {
    const { screen } = twoSlotScreen();
    removeBlock(screen, "c"); // r2 опустеет → удалится
    expect(screen.rows).toHaveLength(1);
    removeBlock(screen, "a");
    expect(screen.rows[0].blocks.map((x) => x.id)).toEqual(["b"]);
  });
});

// Приёмка US-006: «Пожарный журнал» (schema-doc §8.2) собирается ТОЛЬКО через
// примитивы редактора (палитра → appendBlockAsRow/insertBlockInRow, resize через
// дефолтные span, addColumn для таблицы) — без ручной правки JSON.
describe("приёмка: сборка экрана «Осмотр помещений» через примитивы редактора", () => {
  function paletteItem(key: string) {
    for (const group of PALETTE) {
      const item = group.items.find((i) => i.key === key);
      if (item) return item;
    }
    throw new Error(`palette item ${key} not found`);
  }

  test("секция + dictionary/date + таблица «Помещения» + file", () => {
    const screen: Screen = { rows: [] };

    // 1) Секция «Общие сведения» — новым рядом (span 12 по умолчанию).
    const section = createBlock(paletteItem("section"));
    if (section.kind === "section") section.title = "Общие сведения";
    appendBlockAsRow(screen, section);

    // 2) Ряд «Проверяющий (справочник) + Дата»: два поля span-6 в одном ряду.
    const inspector = createBlock(paletteItem("dictionary")); // span 6 по умолчанию
    appendBlockAsRow(screen, inspector);
    const date = createBlock(paletteItem("date")); // span 6
    insertBlockInRow(screen, screen.rows[1].id, date); // 6 + 6 = 12, помещается

    // 3) Таблица «Помещения» с тремя колонками.
    const table = createBlock(paletteItem("table"));
    if (table.kind === "table") {
      table.table.label = "Помещения";
      addColumn(table.table, "boolean"); // огнетушитель
      addColumn(table.table, "text"); // замечание
    }
    appendBlockAsRow(screen, table);

    // 4) Файл «Фото нарушений».
    const file = createBlock(paletteItem("file"));
    appendBlockAsRow(screen, file);

    // Структура совпадает с эталоном §8.2 (без правки JSON).
    expect(screen.rows).toHaveLength(4);
    expect(screen.rows[0].blocks[0].kind).toBe("section");
    expect(screen.rows[0].blocks[0].span).toBe(12);

    const secondRow = screen.rows[1];
    expect(secondRow.blocks).toHaveLength(2);
    expect(secondRow.blocks.map((b) => b.span)).toEqual([6, 6]);
    expect(rowUsedSpan(secondRow)).toBe(12);
    const [dictBlock, dateBlock] = secondRow.blocks;
    expect(dictBlock.kind === "field" && dictBlock.field.type).toBe("dictionary");
    expect(dateBlock.kind === "field" && dateBlock.field.type).toBe("date");

    const tableBlock = screen.rows[2].blocks[0];
    expect(tableBlock.kind).toBe("table");
    if (tableBlock.kind === "table") {
      expect(tableBlock.table.label).toBe("Помещения");
      expect(tableBlock.table.columns).toHaveLength(3);
    }

    const fileBlock = screen.rows[3].blocks[0];
    expect(fileBlock.kind === "field" && fileBlock.field.type).toBe("file");
  });
});

describe("фабрики полей и колонок таблицы", () => {
  test("createField проставляет type-специфичные слоты", () => {
    expect(createField("select").options).toBeDefined();
    expect(createField("dictionary").source).toBeDefined();
    expect(createField("computed").expr).toBeDefined();
    expect(createField("text").options).toBeUndefined();
  });

  test("createBlock таблицы даёт TableBlock с одной колонкой", () => {
    const block = createBlock(PALETTE[2].items[1]);
    expect(block.kind).toBe("table");
    if (block.kind === "table") {
      expect(block.table.columns).toHaveLength(1);
    }
  });

  test("add/removeColumn мутируют columns", () => {
    const table: TableBlock = createBlock(PALETTE[2].items[1]).kind === "table"
      ? (createBlock(PALETTE[2].items[1]) as Extract<Block, { kind: "table" }>).table
      : ({} as TableBlock);
    const before = table.columns.length;
    addColumn(table, "number");
    expect(table.columns).toHaveLength(before + 1);
    removeColumn(table, table.columns[0].id);
    expect(table.columns).toHaveLength(before);
  });
});
