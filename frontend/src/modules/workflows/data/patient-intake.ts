import type { JournalSchema } from '@/modules/workflows/types/journal'

export const patientIntake: JournalSchema = {
  "id": "patient-intake-v1",
  "title": "Журнал первичного приёма",
  "version": 1,
  "nodes": [
    { "id": "start", "type": "start", "position": { "x": 0, "y": 260 }, "data": { "label": "Начало" } },
    {
      "id": "anamnesis",
      "type": "step",
      "position": { "x": 220, "y": 200 },
      "data": {
        "label": "Анамнез",
        "fields": [
          { "id": "patientAge", "label": "Возраст пациента", "type": "number", "required": true },
          { "id": "hasTinnitus", "label": "Есть тиннитус", "type": "boolean" }
        ]
      }
    },
    {
      "id": "audiogram",
      "type": "step",
      "position": { "x": 500, "y": 200 },
      "data": {
        "label": "Аудиограмма",
        "fields": [
          { "id": "thresholdRightDb", "label": "Порог справа, дБ", "type": "number", "required": true },
          { "id": "thresholdLeftDb", "label": "Порог слева, дБ", "type": "number", "required": true }
        ]
      }
    },
    {
      "id": "needsReferral",
      "type": "condition",
      "position": { "x": 780, "y": 200 },
      "data": {
        "label": "Тяжёлая потеря слуха?",
        "rule": {
          "or": [
            { ">": [{ "var": "thresholdRightDb" }, 70] },
            { ">": [{ "var": "thresholdLeftDb" }, 70] }
          ]
        }
      }
    },
    {
      "id": "referral",
      "type": "step",
      "position": { "x": 1120, "y": 0 },
      "data": {
        "label": "Направление к ЛОР",
        "fields": [
          { "id": "referralReason", "label": "Причина направления", "type": "text", "required": true }
        ]
      }
    },
    {
      "id": "fitting",
      "type": "step",
      "position": { "x": 1120, "y": 420 },
      "data": {
        "label": "Подбор аппарата",
        "fields": [
          {
            "id": "recommendedDeviceType",
            "label": "Рекомендуемый тип аппарата",
            "type": "select",
            "required": true,
            "options": [
              { "label": "Заушный (BTE)", "value": "bte" },
              { "label": "Внутриушной (ITE)", "value": "ite" }
            ]
          }
        ]
      }
    },
    { "id": "end", "type": "end", "position": { "x": 1480, "y": 220 }, "data": { "label": "Готово" } }
  ],
  "edges": [
    { "id": "e-start-anamnesis", "source": "start", "target": "anamnesis" },
    { "id": "e-anamnesis-audiogram", "source": "anamnesis", "target": "audiogram" },
    { "id": "e-audiogram-needsReferral", "source": "audiogram", "target": "needsReferral" },
    { "id": "e-needsReferral-referral", "source": "needsReferral", "target": "referral", "sourceHandle": "true" },
    { "id": "e-needsReferral-fitting", "source": "needsReferral", "target": "fitting", "sourceHandle": "false" },
    { "id": "e-referral-end", "source": "referral", "target": "end" },
    { "id": "e-fitting-end", "source": "fitting", "target": "end" }
  ]
}

