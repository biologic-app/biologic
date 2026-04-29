import { computed, ref } from "vue";

export interface WorkflowSample {
  id: number;
  code: string;
  type: string;
  lab: string;
  status: "pending" | "registered" | "analyzed" | "completed" | "rejected";
  deadline: string;
}

export interface WorkflowDirection {
  id: number;
  number: string;
  object: string;
  doctor: string;
  branch: string;
  status: "draft" | "registered" | "in_progress" | "completed";
  urgency: "normal" | "urgent";
  collectedAt: string;
  deadline: string;
  protocol: "missing" | "ready" | "issued";
  samples: WorkflowSample[];
}

export interface WorkflowAlert {
  id: number;
  title: string;
  severity: "info" | "warning" | "critical";
  entityType: "direction" | "sample" | "protocol";
  entityId: number;
  date: string;
  hidden?: boolean;
}

export interface WorkflowUser {
  id: number;
  name: string;
  login: string;
  role: string;
  scope: string;
  status: "active" | "missing_scope" | "deleted";
}

const directions = ref<WorkflowDirection[]>([
  {
    id: 1,
    number: "НП-2026-0419",
    object: "Школа N 127, пищеблок",
    doctor: "Анна Смирнова",
    branch: "Центральный филиал",
    status: "draft",
    urgency: "urgent",
    collectedAt: "2026-04-28T09:20:00.000Z",
    deadline: "2026-04-30T18:00:00.000Z",
    protocol: "missing",
    samples: [
      { id: 11, code: "S-0419-1", type: "Смыв", lab: "Микробиология", status: "pending", deadline: "2026-04-30T18:00:00.000Z" },
      { id: 12, code: "S-0419-2", type: "Вода", lab: "Санитарная химия", status: "pending", deadline: "2026-04-30T18:00:00.000Z" },
    ],
  },
  {
    id: 2,
    number: "НП-2026-0416",
    object: "ООО Север, готовая продукция",
    doctor: "Игорь Волков",
    branch: "Северный филиал",
    status: "registered",
    urgency: "normal",
    collectedAt: "2026-04-26T10:10:00.000Z",
    deadline: "2026-05-02T18:00:00.000Z",
    protocol: "missing",
    samples: [
      { id: 21, code: "S-0416-1", type: "Продукт", lab: "Микробиология", status: "registered", deadline: "2026-05-01T18:00:00.000Z" },
      { id: 22, code: "S-0416-2", type: "Сырьё", lab: "Токсикология", status: "analyzed", deadline: "2026-05-02T18:00:00.000Z" },
    ],
  },
  {
    id: 3,
    number: "НП-2026-0408",
    object: "Детский сад N 44",
    doctor: "Мария Орлова",
    branch: "Центральный филиал",
    status: "completed",
    urgency: "normal",
    collectedAt: "2026-04-20T08:40:00.000Z",
    deadline: "2026-04-27T18:00:00.000Z",
    protocol: "ready",
    samples: [
      { id: 31, code: "S-0408-1", type: "Вода", lab: "Санитарная химия", status: "completed", deadline: "2026-04-26T18:00:00.000Z" },
      { id: 32, code: "S-0408-2", type: "Смыв", lab: "Микробиология", status: "completed", deadline: "2026-04-26T18:00:00.000Z" },
    ],
  },
  {
    id: 4,
    number: "НП-2026-0397",
    object: "Кафе Линия",
    doctor: "Анна Смирнова",
    branch: "Южный филиал",
    status: "in_progress",
    urgency: "urgent",
    collectedAt: "2026-04-24T12:00:00.000Z",
    deadline: "2026-04-28T18:00:00.000Z",
    protocol: "missing",
    samples: [
      { id: 41, code: "S-0397-1", type: "Продукт", lab: "Микробиология", status: "rejected", deadline: "2026-04-27T18:00:00.000Z" },
      { id: 42, code: "S-0397-2", type: "Смыв", lab: "Микробиология", status: "registered", deadline: "2026-04-28T18:00:00.000Z" },
    ],
  },
]);

const alerts = ref<WorkflowAlert[]>([
  { id: 1, title: "Брак образца S-0397-1", severity: "critical", entityType: "sample", entityId: 41, date: "2026-04-28T14:00:00.000Z" },
  { id: 2, title: "Просрочен deadline НП-2026-0397", severity: "critical", entityType: "direction", entityId: 4, date: "2026-04-29T09:00:00.000Z" },
  { id: 3, title: "Протокол готов по НП-2026-0408", severity: "info", entityType: "protocol", entityId: 3, date: "2026-04-28T16:30:00.000Z" },
]);

const users = ref<WorkflowUser[]>([
  { id: 1, name: "Анна Смирнова", login: "asmirnova", role: "Санитарный врач", scope: "Объекты ЦФ", status: "active" },
  { id: 2, name: "Павел Соколов", login: "psokolov", role: "Врач-лаборант", scope: "Микробиология", status: "active" },
  { id: 3, name: "Елена Кузнецова", login: "ekuznetsova", role: "Ассистент-лаборант", scope: "Не назначен", status: "missing_scope" },
]);

export function useWorkflowMock() {
  const visibleAlerts = computed(() => alerts.value.filter((alert) => !alert.hidden));

  function addDirection() {
    directions.value.unshift({
      id: Date.now(),
      number: `НП-2026-${Math.floor(1000 + Math.random() * 8999)}`,
      object: "Новый объект",
      doctor: "Анна Смирнова",
      branch: "Центральный филиал",
      status: "draft",
      urgency: "normal",
      collectedAt: new Date().toISOString(),
      deadline: new Date(Date.now() + 86400000 * 3).toISOString(),
      protocol: "missing",
      samples: [
        { id: Date.now() + 1, code: "S-new-1", type: "Смыв", lab: "Микробиология", status: "pending", deadline: new Date(Date.now() + 86400000 * 3).toISOString() },
      ],
    });
  }

  function registerDirection(direction: WorkflowDirection) {
    direction.status = "registered";
    direction.samples.forEach((sample) => {
      if (sample.status === "pending") sample.status = "registered";
    });
  }

  function updateSample(sample: WorkflowSample, status: WorkflowSample["status"]) {
    sample.status = status;
  }

  function issueProtocol(direction: WorkflowDirection) {
    direction.protocol = "issued";
  }

  function hideAlert(alert: WorkflowAlert) {
    alert.hidden = true;
  }

  return {
    alerts,
    directions,
    hideAlert,
    issueProtocol,
    registerDirection,
    updateSample,
    users,
    visibleAlerts,
    addDirection,
  };
}
