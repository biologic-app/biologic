import type { ApiReadResponse, ApiViewResponse } from "@/shared/types/api";
import type { User } from "@/shared/types";

type MockRow = {
  id: number;
  [key: string]: unknown;
};

const names = [
  "Алексей",
  "Мария",
  "Иван",
  "Елена",
  "Дмитрий",
  "Анна",
  "Сергей",
  "Ольга",
  "Павел",
  "Наталья",
  "Роман",
  "Виктория",
  "Кирилл",
  "Татьяна",
  "Михаил",
  "Юлия",
  "Артём",
  "Дарья",
  "Никита",
  "София",
];

const surnames = [
  "Иванов",
  "Петрова",
  "Смирнов",
  "Кузнецова",
  "Соколов",
  "Попова",
  "Лебедев",
  "Новикова",
  "Морозов",
  "Волкова",
  "Фёдоров",
  "Алексеева",
  "Семёнов",
  "Павлова",
  "Козлов",
  "Орлова",
  "Макаров",
  "Зайцева",
  "Николаев",
  "Васильева",
];

const labNames = ["Биохимия", "Микробиология", "Гематология", "ПЦР", "Токсикология"];
const statusNames = ["Черновик", "Зарегистрирован", "В работе", "Проверен", "Завершён"];
const branchNames = ["Центральный", "Северный", "Южный", "Восточный", "Западный"];
const sampleTypeNames = ["Кровь", "Сыворотка", "Моча", "Мазок", "Вода"];

const pad = (value: number) => String(value).padStart(3, "0");
const date = (index: number) => `2026-04-${String((index % 28) + 1).padStart(2, "0")}`;
const timestamp = (index: number) => `${date(index)}T${String(8 + (index % 10)).padStart(2, "0")}:30:00Z`;
const pick = <T>(items: T[], index: number) => items[(index - 1) % items.length];

const named = (id: number, name: string, extra: Record<string, unknown> = {}) => ({
  id,
  name,
  ...extra,
});

const getPathValue = (row: MockRow, path: string) =>
  path.split(".").reduce<unknown>((value, key) => {
    if (value && typeof value === "object" && key in value) {
      return (value as Record<string, unknown>)[key];
    }

    return undefined;
  }, row);

const meta = (total: number, offset: number, limit: number) => ({
  timestamp: new Date().toISOString(),
  requestId: "mock-data",
  version: "mock",
  includesRequested: [],
  includesApplied: [],
  includesAllowed: [],
  total,
  offset,
  limit,
});

const formatStatusContext = (value: unknown) => {
  if (value === "directions") {
    return "направления";
  }
  if (value === "samples") {
    return "образца";
  }
  if (value === "research") {
    return "исследования";
  }

  return "записи";
};

const createRows = (path: string, params: Record<string, unknown> = {}): MockRow[] | null => {
  const normalizedPath = path.replace(/^\/api\/v1/, "").replace(/\/+$/, "") || "/";

  return Array.from({ length: 20 }, (_, zeroIndex) => {
    const index = zeroIndex + 1;
    const code = `BIO-${pad(index)}`;
    const firstName = pick(names, index);
    const lastName = pick(surnames, index);
    const lab = named((index % 5) + 1, pick(labNames, index));
    const branch = named((index % 5) + 1, `${pick(branchNames, index)} филиал`, { code: `BR-${pad(index)}` });
    const status = named((index % 5) + 1, pick(statusNames, index), {
      code: `ST-${pad(index)}`,
      entity_type: params.entity_type ?? "common",
    });
    const sampleType = named((index % 5) + 1, pick(sampleTypeNames, index), { code: `SM-${pad(index)}` });
    const direction = named(index, `Направление ${2026}-${pad(index)}`);
    const sample = named(index, `Образец ${pad(index)}`);
    const result = named(index, `Результат ${pad(index)}`);
    const indicator = named(index, `Показатель ${pad(index)}`);
    const protocolType = named((index % 5) + 1, `Тип протокола ${index}`, { code: `PT-${pad(index)}` });
    const conclusion = named(index, `Заключение ${pad(index)}`);
    const researchGoal = named(index, `Цель исследования ${pad(index)}`);

    const common = {
      id: index,
      code,
      name: `Запись ${pad(index)}`,
      updated_at: timestamp(index),
    };

    const byPath: Record<string, MockRow> = {
      "/branches": {
        ...common,
        name: `${pick(branchNames, index)} филиал`,
        code: `BR-${pad(index)}`,
      },
      "/statuses": {
        ...common,
        name: `${pick(statusNames, index)} ${formatStatusContext(params.entity_type)}`,
        code: `ST-${pad(index)}`,
        entity_type: params.entity_type ?? "common",
      },
      "/conclusion_statuses": {
        ...common,
        name: `Статус заключения ${pad(index)}`,
        code: `CS-${pad(index)}`,
      },
      "/doctors": {
        ...common,
        first_name: firstName,
        last_name: lastName,
        patronymic: index % 2 ? "Андреевич" : "Сергеевна",
      },
      "/labs": {
        ...common,
        name: `${pick(labNames, index)} ${index}`,
        full_name: `Лаборатория ${pick(labNames, index)} ${index}`,
        branch,
        branch_id: branch.id,
      },
      "/objects": {
        ...common,
        name: `Объект ${pad(index)}`,
        full_name: `Испытательный объект ${pad(index)}`,
        address: `г. Москва, ул. Лабораторная, ${index}`,
        branch,
        branch_id: branch.id,
      },
      "/sample_types": {
        ...common,
        name: pick(sampleTypeNames, index),
        code: `SM-${pad(index)}`,
      },
      "/research_goals": {
        ...common,
        name: `Цель исследования ${pad(index)}`,
        comment: `Плановая проверка показателя ${index}`,
        lab,
        lab_id: lab.id,
      },
      "/indicators": {
        ...common,
        name: `Показатель ${pad(index)}`,
        unit: index % 2 ? "мг/л" : "КОЕ/мл",
        norm_text: "В пределах референса",
        norm_value: `${index * 2}`,
        lab,
        lab_id: lab.id,
        sample_type: sampleType,
        sample_type_id: sampleType.id,
      },
      "/protocol_types": {
        ...common,
        name: `Тип протокола ${index}`,
        code: `PT-${pad(index)}`,
      },
      "/conclusions": {
        ...common,
        comment: `Формулировка заключения ${pad(index)}`,
        conclusion_status: status,
        conclusion_status_id: status.id,
      },
      "/directions": {
        ...common,
        year_no: 2026,
        base_no: 1000 + index,
        doctor: named(index, `${lastName} ${firstName}`),
        doctor_id: index,
        object: named(index, `Объект ${pad(index)}`),
        object_id: index,
        status,
        status_id: status.id,
        sampled_at: date(index),
        received_at: date(index + 1),
        completed_at: index % 3 === 0 ? date(index + 4) : null,
        is_done: index % 3 === 0,
        is_urgent: index % 4 === 0,
      },
      "/samples": {
        ...common,
        month_no: (index % 12) + 1,
        name: `Образец ${pad(index)}`,
        alternate_name: `Sample ${pad(index)}`,
        mass: `${100 + index} г`,
        target_description: `Контрольная проба ${index}`,
        sample_type: sampleType,
        sample_type_id: sampleType.id,
        direction,
        direction_id: direction.id,
        protocol: named(index, `Протокол ${pad(index)}`),
        protocol_id: index,
        status,
        status_id: status.id,
        is_urgent: index % 4 === 0,
        is_done: index % 3 === 0,
        received_at: date(index),
      },
      "/protocols": {
        ...common,
        year_no: 2026,
        copies: (index % 4) + 1,
        protocol_type: protocolType,
        protocol_type_id: protocolType.id,
        conclusion,
        conclusion_id: conclusion.id,
        is_signed: index % 2 === 0,
        issued_at: date(index + 2),
      },
      "/results": {
        ...common,
        name: `Результат ${pad(index)}`,
        sample,
        sample_id: sample.id,
        lab,
        lab_id: lab.id,
        status,
        status_id: status.id,
        is_done: index % 3 === 0,
        received_at: date(index),
        completed_at: index % 3 === 0 ? date(index + 3) : null,
      },
      "/tests": {
        ...common,
        result,
        result_id: result.id,
        indicator,
        indicator_id: indicator.id,
        status,
        status_id: status.id,
        value: (index * 1.7).toFixed(1),
        norm: "0-10",
        is_active: index % 5 !== 0,
      },
      "/sample_targets": {
        ...common,
        sample,
        sample_id: sample.id,
        research_goal: researchGoal,
        research_goal_id: researchGoal.id,
        status,
        status_id: status.id,
      },
      "/roles": {
        ...common,
        key: `role_${pad(index)}`,
        name: `Роль ${pad(index)}`,
        permissionsSummary: {
          view: 8 + (index % 8),
          create: 3 + (index % 5),
          edit: 2 + (index % 4),
          delete: index % 3,
        },
      },
      "/user-types": {
        ...common,
        key: `role_${pad(index)}`,
        name: `Роль ${pad(index)}`,
        permissionsSummary: {
          view: 8 + (index % 8),
          create: 3 + (index % 5),
          edit: 2 + (index % 4),
          delete: index % 3,
        },
      },
      "/users": {
        ...common,
        username: `user${pad(index)}`,
        email: `user${pad(index)}@bio.local`,
        first_name: firstName,
        last_name: lastName,
        patronymic: index % 2 ? "Андреевич" : "Сергеевна",
        role: named((index % 5) + 1, `Роль ${pad((index % 5) + 1)}`),
        role_id: (index % 5) + 1,
        lab,
        lab_id: lab.id,
        is_registrar: index % 2 === 0,
        is_lab_head: index % 5 === 0,
        is_branch_head: index % 7 === 0,
        overridesCount: index % 4,
      },
    };

    return byPath[normalizedPath] ?? null;
  }).filter((row): row is MockRow => Boolean(row));
};

const applyFilters = (rows: MockRow[], params: Record<string, unknown>) => {
  let filtered = [...rows];
  const global = String(params.global ?? "").trim().toLowerCase();

  if (global) {
    filtered = filtered.filter((row) => JSON.stringify(row).toLowerCase().includes(global));
  }

  if (typeof params.filters === "string") {
    try {
      const filters = JSON.parse(params.filters) as Record<string, unknown>;
      filtered = filtered.filter((row) =>
        Object.entries(filters).every(([field, value]) => {
          const current = getPathValue(row, field);

          if (Array.isArray(value)) {
            const filled = value.filter((item) => item !== null && item !== "" && item !== undefined);

            if (filled.length === 2 && String(field).includes("_at")) {
              const currentTime = current ? new Date(String(current)).getTime() : 0;
              const [from, to] = filled;
              return (
                (!from || currentTime >= new Date(String(from)).getTime()) &&
                (!to || currentTime <= new Date(String(to)).getTime())
              );
            }

            return filled.length ? filled.includes(current) : true;
          }

          return String(current ?? "").toLowerCase().includes(String(value).toLowerCase());
        }),
      );
    } catch {
      return filtered;
    }
  }

  return filtered;
};

const applySort = (rows: MockRow[], params: Record<string, unknown>) => {
  const field = String(params.sort_by ?? "");
  if (!field) {
    return rows;
  }

  const direction = params.sort_order === "desc" || params.sort_order === -1 ? -1 : 1;

  return [...rows].sort((a, b) => {
    const aValue = getPathValue(a, field);
    const bValue = getPathValue(b, field);

    return String(aValue ?? "").localeCompare(String(bValue ?? ""), "ru") * direction;
  });
};

export const getMockListResponse = <T>(
  path: string,
  params: Record<string, unknown> = {},
): ApiViewResponse<T> | null => {
  const rows = createRows(path, params);

  if (!rows || rows.length === 0) {
    return null;
  }

  const filtered = applySort(applyFilters(rows, params), params);
  const offset = Number(params.offset ?? 0);
  const limit = Number(params.limit ?? 20);
  const items = filtered.slice(offset, offset + limit);

  return {
    items: items as T[],
    meta: meta(filtered.length, offset, limit),
  };
};

export const getMockReadResponse = <T>(path: string): ApiReadResponse<T> | null => {
  const roleMatch = path.match(/^\/roles\/\d+\/permissions$/);
  const userMatch = path.match(/^\/users\/\d+\/permissions$/);

  if (!roleMatch && !userMatch) {
    return null;
  }

  const permissions = (["view", "create", "edit", "delete"] as const).flatMap((action) =>
    (["directions", "samples", "results", "tests", "protocols"] as const).map((resource) => ({
      resource,
      action,
    })),
  );

  return {
    data: (roleMatch ? { permissions } : { rolePermissions: permissions, overrides: [] }) as T,
    meta: {
      timestamp: new Date().toISOString(),
      requestId: "mock-data",
      version: "mock",
      includesRequested: [],
      includesApplied: [],
      includesAllowed: [],
      includes: [],
    },
  };
};

export const createMockCustomers = (): User[] =>
  Array.from({ length: 20 }, (_, zeroIndex) => {
    const index = zeroIndex + 1;
    const firstName = pick(names, index);
    const lastName = pick(surnames, index);

    return {
      id: index,
      name: `${firstName} ${lastName}`,
      email: `patient${pad(index)}@bio.local`,
      location: ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Екатеринбург"][
        zeroIndex % 5
      ],
      status: (["subscribed", "unsubscribed", "bounced"] as const)[zeroIndex % 3],
      avatar: {
        src: `https://i.pravatar.cc/96?img=${index}`,
        alt: `${firstName} ${lastName}`,
      },
    };
  });
