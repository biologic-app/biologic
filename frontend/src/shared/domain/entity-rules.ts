import { i18n } from "@/shared/i18n";

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString();

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

type EntityRuleDefinition = Omit<EntityRule, "deleteRestriction"> & {
  // i18n-ключ (не готовый текст) — резолвится в getEntityRule() через t(),
  // чтобы переключение языка применялось сразу.
  deleteRestrictionKey?: string;
};

const entityRuleDefinitions: Record<string, EntityRuleDefinition> = {
  directions: {
    deletableStatuses: ["draft"],
    deleteRestrictionKey: "entityRules.directionsDeleteRestriction",
    detailKind: "directions",
  },
  samples: {
    deletableStatuses: ["pending"],
    deleteRestrictionKey: "entityRules.samplesDeleteRestriction",
    detailKind: "samples",
    // Образцы создаются только импортом направления или вручную внутри карточки
    // направления — не со страницы «Образцы» (см. docs/flows/registrator.flow.md).
    createDisabled: true,
  },
  research: {
    deletableStatuses: ["draft"],
    deleteRestrictionKey: "entityRules.researchDeleteRestriction",
    detailKind: "research",
    // Исследования создаются только через POST /samples/{id}/assign-research —
    // standalone POST /research backend больше не поддерживает.
    createDisabled: true,
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

export const getEntityRule = (presetKey: string): EntityRule => {
  const { deleteRestrictionKey, ...rest } = entityRuleDefinitions[presetKey] ?? {};
  return {
    ...rest,
    ...(deleteRestrictionKey ? { deleteRestriction: t(deleteRestrictionKey) } : {}),
  };
};
