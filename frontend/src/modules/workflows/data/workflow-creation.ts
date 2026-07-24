import type { JournalSchema } from '@/modules/workflows/types/journal'

export const workflowCreation: JournalSchema = {
  "id": "workflow-creation-v1",
  "title": "Создание рабочего процесса",
  "version": 1,
  "nodes": [
    { "id": "start", "type": "start", "position": { "x": 0, "y": 220 }, "data": { "label": "Начало" } },
    {
      "id": "basics",
      "type": "step",
      "position": { "x": 260, "y": 160 },
      "data": {
        "label": "Основные сведения",
        "fields": [
          { "id": "processTitle", "label": "Название процесса", "type": "text", "required": true },
          { "id": "processPurpose", "label": "Назначение / для чего нужен журнал", "type": "textarea", "required": true }
        ]
      }
    },
    {
      "id": "recordFields",
      "type": "step",
      "position": { "x": 540, "y": 160 },
      "data": {
        "label": "Поля записи",
        "fields": [
          { "id": "firstFieldLabel", "label": "Первое поле записи", "type": "text", "required": true },
          {
            "id": "firstFieldType",
            "label": "Тип первого поля",
            "type": "select",
            "required": true,
            "options": [
              { "label": "Текст", "value": "text" },
              { "label": "Число", "value": "number" },
              { "label": "Да / Нет", "value": "boolean" },
              { "label": "Список", "value": "select" },
              { "label": "Дата", "value": "date" }
            ]
          }
        ]
      }
    },
    {
      "id": "needsBuilder",
      "type": "condition",
      "position": { "x": 820, "y": 160 },
      "data": {
        "label": "Нужен графический конструктор шагов?",
        "rule": {
          "==": [{ "var": "firstFieldType" }, "select"]
        }
      }
    },
    {
      "id": "builderNotes",
      "type": "step",
      "position": { "x": 1120, "y": 0 },
      "data": {
        "label": "Заметки для конструктора",
        "fields": [
          { "id": "builderNotes", "label": "Что настроить в конструкторе (шаги, условия, циклы)", "type": "textarea" }
        ]
      }
    },
    {
      "id": "review",
      "type": "step",
      "position": { "x": 1120, "y": 340 },
      "data": {
        "label": "Проверка перед публикацией",
        "fields": [
          { "id": "reviewedBy", "label": "Кто проверил", "type": "text", "required": true },
          { "id": "readyToPublish", "label": "Готов к публикации", "type": "boolean" }
        ]
      }
    },
    { "id": "end", "type": "end", "position": { "x": 1460, "y": 170 }, "data": { "label": "Процесс создан" } }
  ],
  "edges": [
    { "id": "e-start-basics", "source": "start", "target": "basics" },
    { "id": "e-basics-recordFields", "source": "basics", "target": "recordFields" },
    { "id": "e-recordFields-needsBuilder", "source": "recordFields", "target": "needsBuilder" },
    { "id": "e-needsBuilder-builderNotes", "source": "needsBuilder", "target": "builderNotes", "sourceHandle": "true" },
    { "id": "e-needsBuilder-review", "source": "needsBuilder", "target": "review", "sourceHandle": "false" },
    { "id": "e-builderNotes-review", "source": "builderNotes", "target": "review" },
    { "id": "e-review-end", "source": "review", "target": "end" }
  ]
}
