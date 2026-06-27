// Правила сущностей, вынесенные из per-preset веток god-компонента
// (Open/Closed): удаление по статусу, тип карточки, запрет ручного создания.
// Добавление сущности = строка здесь, а не новый `if (presetKey === …)`.
export type EntityDetailKind = "directions" | "samples" | "research";

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
  },
  research: {
    deletableStatuses: ["draft"],
    deleteRestriction: "Удалять можно только исследования в статусе «Черновик».",
    detailKind: "research",
  },
  tests: {
    createDisabled: true,
  },
};

export const getEntityRule = (presetKey: string): EntityRule =>
  entityRules[presetKey] ?? {};
