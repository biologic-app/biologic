// Правила сущностей, вынесенные из per-preset веток god-компонента
// (Open/Closed): удаление по статусу, тип карточки, запрет ручного создания.
// Добавление сущности = строка здесь, а не новый `if (presetKey === …)`.
export type EntityDetailKind = "directions" | "samples" | "research" | "protocols";

export type EntityRule = {
  // Статусы, в которых запись можно удалить. undefined ⇒ удаление всегда разрешено.
  deletableStatuses?: string[];
  // Сообщение при попытке удалить запись в недопустимом статусе.
  deleteRestriction?: string;
  // Бизнес-сущность (отдельная карточка). Иначе — модалка справочника.
  detailKind?: EntityDetailKind;
  // Создание записей доступно только через рабочий процесс (кнопка «Создать» скрыта).
  createDisabled?: boolean;
};

export const entityRules: Record<string, EntityRule> = {
  directions: {
    deletableStatuses: ["draft"],
    deleteRestriction: "Удалять можно только направления в статусе «Черновик».",
    detailKind: "directions",
  },
  samples: {
    deletableStatuses: ["pending"],
    deleteRestriction: "Удалять можно только образцы в статусе «На регистрации».",
    detailKind: "samples",
    // Образцы создаются только импортом направления или вручную внутри карточки
    // направления — не со страницы «Образцы» (см. docs/flows/registrator.flow.md).
    createDisabled: true,
  },
  research: {
    deletableStatuses: ["draft"],
    deleteRestriction: "Удалять можно только исследования в статусе «Черновик».",
    detailKind: "research",
  },
  tests: {
    createDisabled: true,
  },
  protocols: {
    detailKind: "protocols",
    // Протокол связывает несколько образцов одним POST /protocols
    // (sample_ids) — создаётся через выделение образцов на /samples
    // (см. DictionaryCrudContent.vue), не через общую форму «Создать».
    createDisabled: true,
  },
};

export const getEntityRule = (presetKey: string): EntityRule =>
  entityRules[presetKey] ?? {};
