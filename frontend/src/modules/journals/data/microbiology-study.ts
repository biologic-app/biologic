import type { JournalSchema } from '@/modules/journals/types/journal'

export const microbiologyStudy: JournalSchema = {
  "id": "microbiology-study-v1",
  "title": "Журнал микробиологического исследования",
  "version": 1,
  "nodes": [
    { "id": "start", "type": "start", "position": { "x": 0, "y": 420 }, "data": { "label": "Начало" } },

    {
      "id": "posev",
      "type": "step",
      "position": { "x": 360, "y": 360 },
      "data": {
        "label": "Первичный посев",
        "role": "lab_assistant",
        "fields": [
          {
            "id": "sourceType",
            "label": "Источник материала",
            "type": "select",
            "required": true,
            "options": [
              { "label": "Продукты с продбазы", "value": "products" },
              { "label": "Вода и образцы с объектов", "value": "water_objects" }
            ]
          },
          { "id": "sampleNumber", "label": "Номер пробы", "type": "text", "required": true },
          { "id": "seedingDate", "label": "Дата посева", "type": "date", "required": true },
          {
            "id": "media",
            "label": "Среда посева",
            "type": "select",
            "required": true,
            "options": [
              { "label": "Чашки", "value": "plates" },
              { "label": "Бульоны", "value": "broth" },
              { "label": "Чашки и бульоны", "value": "plates_and_broth" }
            ]
          }
        ]
      }
    },

    {
      "id": "bouillonControl",
      "type": "step",
      "position": { "x": 760, "y": 380 },
      "data": {
        "label": "Контроль бульона",
        "description": "На следующий день после посева",
        "role": "lab_assistant",
        "fields": [
          { "id": "bouillonTurbid", "label": "Бульон дал помутнение (плюсанул)", "type": "boolean", "required": true }
        ]
      }
    },

    {
      "id": "needsReseed",
      "type": "condition",
      "position": { "x": 1140, "y": 380 },
      "data": {
        "label": "Бульон плюсанул?",
        "rule": { "==": [{ "var": "bouillonTurbid" }, true] }
      }
    },

    {
      "id": "reseed",
      "type": "step",
      "position": { "x": 1540, "y": 60 },
      "data": {
        "label": "Пересев",
        "role": "lab_assistant",
        "fields": [
          { "id": "reseedDate", "label": "Дата пересева", "type": "date", "required": true },
          { "id": "reseedMedia", "label": "Среда/чашка для пересева", "type": "text", "required": true }
        ]
      }
    },

    {
      "id": "identification",
      "type": "step",
      "position": { "x": 1940, "y": 60 },
      "data": {
        "label": "Идентификация (мазок)",
        "role": "doctor",
        "fields": [
          { "id": "smearResult", "label": "Результат мазка", "type": "text", "required": true },
          { "id": "organismName", "label": "Название микроорганизма", "type": "text" }
        ]
      }
    },

    {
      "id": "isPathogenFound",
      "type": "condition",
      "position": { "x": 2340, "y": 60 },
      "data": {
        "label": "Обнаружен возбудитель?",
        "rule": { "!!": { "var": "organismName" } }
      }
    },

    {
      "id": "additionalTests",
      "type": "loop",
      "position": { "x": 2740, "y": -320 },
      "data": {
        "label": "Дополнительные тесты",
        "description": "Врач гоняет столько тестов, сколько сочтёт нужным",
        "role": "doctor",
        "itemNoun": "тест",
        "fields": [
          { "id": "extraTestName", "label": "Тест", "type": "text", "required": true },
          { "id": "extraTestResult", "label": "Результат", "type": "text", "required": true }
        ]
      }
    },

    {
      "id": "conclusionNonCompliant",
      "type": "step",
      "position": { "x": 3160, "y": -280 },
      "data": {
        "label": "Заключение: несоответствие",
        "role": "doctor",
        "fields": [
          {
            "id": "complianceStatus",
            "label": "Статус соответствия",
            "type": "select",
            "required": true,
            "options": [{ "label": "Не соответствует", "value": "non_compliant" }]
          },
          { "id": "comment", "label": "Комментарий для протокола", "type": "text", "required": true }
        ]
      }
    },

    {
      "id": "conclusionNormal",
      "type": "step",
      "position": { "x": 2740, "y": 520 },
      "data": {
        "label": "Заключение: норма",
        "role": "doctor",
        "fields": [
          {
            "id": "complianceStatus",
            "label": "Статус соответствия",
            "type": "select",
            "required": true,
            "options": [{ "label": "Соответствует", "value": "compliant" }]
          },
          { "id": "comment", "label": "Комментарий для протокола", "type": "text" }
        ]
      }
    },

    { "id": "end", "type": "end", "position": { "x": 3560, "y": 200 }, "data": { "label": "Готово" } }
  ],
  "edges": [
    { "id": "e-start-posev", "source": "start", "target": "posev" },
    { "id": "e-posev-bouillonControl", "source": "posev", "target": "bouillonControl" },
    { "id": "e-bouillonControl-needsReseed", "source": "bouillonControl", "target": "needsReseed" },

    { "id": "e-needsReseed-reseed", "source": "needsReseed", "target": "reseed", "sourceHandle": "true" },
    { "id": "e-needsReseed-conclusionNormal", "source": "needsReseed", "target": "conclusionNormal", "sourceHandle": "false" },

    { "id": "e-reseed-identification", "source": "reseed", "target": "identification" },
    { "id": "e-identification-isPathogenFound", "source": "identification", "target": "isPathogenFound" },

    { "id": "e-isPathogenFound-additionalTests", "source": "isPathogenFound", "target": "additionalTests", "sourceHandle": "true" },
    { "id": "e-isPathogenFound-normal", "source": "isPathogenFound", "target": "conclusionNormal", "sourceHandle": "false" },

    { "id": "e-additionalTests-nonCompliant", "source": "additionalTests", "target": "conclusionNonCompliant" },

    { "id": "e-conclusionNonCompliant-end", "source": "conclusionNonCompliant", "target": "end" },
    { "id": "e-conclusionNormal-end", "source": "conclusionNormal", "target": "end" }
  ]
}

