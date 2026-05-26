import type { CrudModuleConfig } from "@/pages/CrudModulePage.vue";
import { crudModules } from "@/shared/config/crud-modules";

type CrudModuleKey = keyof typeof crudModules;

export interface DictionaryItem {
  key: string;
  configKey: CrudModuleKey;
  label: string;
  icon: string;
  requestParams?: Record<string, string>;
  config?: Partial<Pick<CrudModuleConfig, "title" | "description" | "presetKey" | "pageId">>;
}

const statusContexts: DictionaryItem[] = [
  {
    key: "statuses-directions",
    configKey: "direction-statuses",
    label: "Для направлений",
    icon: "i-lucide-book-copy",
    config: {
      title: "Статусы направлений",
      description: "Статусы жизненного цикла направлений.",
      presetKey: "statuses-directions",
      pageId: "statuses-directions",
    },
  },
  {
    key: "statuses-samples",
    configKey: "sample-statuses",
    label: "Для образцов",
    icon: "i-lucide-vial",
    config: {
      title: "Статусы образцов",
      description: "Статусы приёмки, работы и закрытия образцов.",
      presetKey: "statuses-samples",
      pageId: "statuses-samples",
    },
  },
  {
    key: "statuses-research",
    configKey: "research-statuses",
    label: "Для исследований",
    icon: "i-lucide-flask-conical",
    config: {
      title: "Статусы исследований",
      description: "Статусы лабораторных исследований и результатов.",
      presetKey: "statuses-research",
      pageId: "statuses-research",
    },
  },
  {
    key: "statuses-tests",
    configKey: "test-statuses",
    label: "Для тестов",
    icon: "i-lucide-list-checks",
    config: {
      title: "Статусы тестов",
      description: "Статусы отдельных лабораторных тестов.",
      presetKey: "statuses-tests",
      pageId: "statuses-tests",
    },
  },
];

export const dictionaryItems: DictionaryItem[] = [
  { key: "objects", configKey: "objects", label: "Объекты", icon: "i-lucide-building-2" },
  { key: "sample-types", configKey: "sample-types", label: "Типы образцов", icon: "i-lucide-tags" },
  { key: "branches", configKey: "branches", label: "Филиалы", icon: "i-lucide-map-pin" },
  { key: "doctors", configKey: "doctors", label: "Врачи", icon: "i-lucide-user-round" },
  { key: "labs", configKey: "labs", label: "Лаборатории", icon: "i-lucide-test-tube-2" },
  { key: "research-goals", configKey: "research-goals", label: "Цели исследований", icon: "i-lucide-crosshair" },
  { key: "indicators", configKey: "indicators", label: "Показатели", icon: "i-lucide-list-checks" },
  { key: "conclusions", configKey: "conclusions", label: "Заключения", icon: "i-lucide-file-text" },
  {
    key: "statuses",
    configKey: "direction-statuses",
    label: "Статусы",
    icon: "i-lucide-badge-check",
    config: {
      title: "Статусы",
      description: "Выберите тип статусов в навигации сверху.",
    },
  },
  { key: "protocol-types", configKey: "protocol-types", label: "Типы протоколов", icon: "i-lucide-file-badge" },
];

export const statusDictionaryItems = statusContexts;

export const allDictionaryItems = [...dictionaryItems, ...statusDictionaryItems];

export const defaultDictionaryKey = dictionaryItems[0].key;

export const getDictionaryItem = (key: string) =>
  allDictionaryItems.find((item) => item.key === key);

export const getDictionaryConfig = (item: DictionaryItem): CrudModuleConfig => ({
  ...crudModules[item.configKey],
  ...(item.config || {}),
});

export const isDictionaryKey = (key: string) => Boolean(getDictionaryItem(key));
