import { reactive } from "vue";
import { getValueByPath } from "@/shared/utils/object";
import {
  normalizeFormValue,
  type DetailFieldValue,
} from "@/shared/ui/entity-detail.helpers";

export type EntityFormField = {
  key: string;
  type?: string;
  required?: boolean;
};

// Общее состояние формы карточки сущности: синхронизация из записи,
// нормализация значений, сборка payload и проверка обязательных полей.
// Вынесено из EntityDetailDialogBase / AccessEntityDetailModal /
// DictionaryCrudDetailModal, где было почти идентично продублировано.
export function useEntityForm() {
  const formState = reactive<Record<string, DetailFieldValue>>({});

  // Заполняет formState значениями записи. initialValues (create-режим)
  // перекрывают значения из row для перечисленных ключей.
  function sync(
    fields: EntityFormField[],
    row: Record<string, unknown> | null,
    initialValues?: Record<string, unknown> | null,
  ) {
    fields.forEach((field) => {
      let value = row ? getValueByPath(row, field.key) : null;
      if (initialValues && field.key in initialValues) {
        value = initialValues[field.key];
      }
      formState[field.key] = normalizeFormValue(value);
    });
  }

  function reset() {
    Object.keys(formState).forEach((key) => delete formState[key]);
  }

  function formString(key: string) {
    const value = formState[key];
    return typeof value === "string" || typeof value === "number" ? String(value) : "";
  }

  function formBoolean(key: string) {
    return Boolean(formState[key]);
  }

  function setValue(key: string, value: unknown) {
    formState[key] = normalizeFormValue(value);
  }

  function buildPayload(fields: EntityFormField[]): Record<string, unknown> {
    return Object.fromEntries(
      fields.map((field) => [field.key, formState[field.key] ?? null]),
    );
  }

  // Обязательные поля, оставшиеся пустыми (для валидации перед сохранением).
  function missingRequired(fields: EntityFormField[]) {
    return fields.filter(
      (field) =>
        field.required
        && (formState[field.key] === null
          || formState[field.key] === undefined
          || formState[field.key] === ""),
    );
  }

  return {
    formState,
    sync,
    reset,
    formString,
    formBoolean,
    setValue,
    buildPayload,
    missingRequired,
  };
}
