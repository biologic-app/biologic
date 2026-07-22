import { i18n } from '@/shared/i18n';
import type { CrudModuleConfig } from '@/shared/types/crud';
import { crudModules } from "@/shared/config/crud-modules";

const t = (key: string, params?: Record<string, unknown>) =>
  i18n.global.t(key, params ?? {}).toString();

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
    label: t("dictionaries.statusesForDirections"),
    icon: "i-lucide-book-copy",
    config: {
      title: t("dictionaries.directionsStatusesTitle"),
      description: t("dictionaries.directionsStatusesDescription"),
      presetKey: "statuses-directions",
      pageId: "statuses-directions",
    },
  },
  {
    key: "statuses-samples",
    configKey: "sample-statuses",
    label: t("dictionaries.statusesForSamples"),
    icon: "i-lucide-test-tube-2",
    config: {
      title: t("dictionaries.samplesStatusesTitle"),
      description: t("dictionaries.samplesStatusesDescription"),
      presetKey: "statuses-samples",
      pageId: "statuses-samples",
    },
  },
  {
    key: "statuses-research",
    configKey: "research-statuses",
    label: t("dictionaries.statusesForResearch"),
    icon: "i-lucide-flask-conical",
    config: {
      title: t("dictionaries.researchStatusesTitle"),
      description: t("dictionaries.researchStatusesDescription"),
      presetKey: "statuses-research",
      pageId: "statuses-research",
    },
  },
  {
    key: "statuses-tests",
    configKey: "test-statuses",
    label: t("dictionaries.statusesForTests"),
    icon: "i-lucide-list-checks",
    config: {
      title: t("dictionaries.testsStatusesTitle"),
      description: t("dictionaries.testsStatusesDescription"),
      presetKey: "statuses-tests",
      pageId: "statuses-tests",
    },
  },
];

export const dictionaryItems: DictionaryItem[] = [
  { key: "objects", configKey: "objects", label: t("dictionaries.objects"), icon: "i-lucide-building-2" },
  { key: "sample-types", configKey: "sample-types", label: t("dictionaries.sampleTypes"), icon: "i-lucide-tags" },
  { key: "branches", configKey: "branches", label: t("dictionaries.branches"), icon: "i-lucide-map-pin" },
  { key: "doctors", configKey: "doctors", label: t("dictionaries.doctors"), icon: "i-lucide-user-round" },
  { key: "labs", configKey: "labs", label: t("dictionaries.labs"), icon: "i-lucide-test-tube-2" },
  { key: "research-goals", configKey: "research-goals", label: t("dictionaries.researchGoals"), icon: "i-lucide-crosshair" },
  { key: "indicators", configKey: "indicators", label: t("dictionaries.indicators"), icon: "i-lucide-list-checks" },
  { key: "conclusions", configKey: "conclusions", label: t("dictionaries.conclusions"), icon: "i-lucide-file-text" },
  {
    key: "statuses",
    configKey: "direction-statuses",
    label: t("dictionaries.statuses"),
    icon: "i-lucide-badge-check",
    config: {
      title: t("dictionaries.statuses"),
      description: t("dictionaries.statusesDescription"),
    },
  },
  { key: "protocol-types", configKey: "protocol-types", label: t("dictionaries.protocolTypes"), icon: "i-lucide-file-badge" },
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
