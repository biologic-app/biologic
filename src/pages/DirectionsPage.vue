<script setup lang="ts">
import { format } from "date-fns";
import type { StepperItem, TabsItem } from "@nuxt/ui";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useWorkflowRole } from "@/modules/workflows/useWorkflowRole";
import { useWorkflowMock, type WorkflowDirection, type WorkflowSample } from "@/modules/workflows/useWorkflowMock";

const route = useRoute();
const router = useRouter();
const toast = useToast();
const { selectedMode, selectedRole, selectedRoleKey } = useWorkflowRole();
const { addDirection, directions, issueProtocol, registerDirection, updateSample } = useWorkflowMock();

type DirectionFilter = "all" | "draft" | "registered" | "in_progress" | "completed";

const query = ref("");
const selectedFilter = ref<DirectionFilter>("all");
const selectedDirection = ref<WorkflowDirection | null>(directions.value[0] ?? null);
const importOpen = ref(false);
const createOpen = ref(false);
const protocolOpen = ref(false);
const activeDirectionTab = ref<"samples" | "history">("samples");

const readonlyMode = computed(() => selectedMode.value === "readonly");
const canEditDirections = computed(() => selectedRoleKey.value === "registrar");
const canSeeProtocol = computed(() => ["registrar", "sanitary_inspector", "branch_chief"].includes(selectedRoleKey.value));

const filterItems = computed(() => [
  { label: "Все", value: "all" },
  { label: "Draft", value: "draft" },
  { label: "Registered", value: "registered" },
  { label: "В работе", value: "in_progress" },
  { label: "Завершено", value: "completed" },
]);

const filteredDirections = computed(() => {
  const normalizedQuery = query.value.trim().toLocaleLowerCase();

  return directions.value.filter((direction) => {
    const matchesFilter = selectedFilter.value === "all" || direction.status === selectedFilter.value;
    const matchesQuery = !normalizedQuery
      || direction.number.toLocaleLowerCase().includes(normalizedQuery)
      || direction.object.toLocaleLowerCase().includes(normalizedQuery)
      || direction.doctor.toLocaleLowerCase().includes(normalizedQuery)
      || direction.branch.toLocaleLowerCase().includes(normalizedQuery);

    if (selectedRoleKey.value === "sanitary_inspector" && direction.doctor !== "Анна Смирнова") {
      return false;
    }

    return matchesFilter && matchesQuery;
  });
});

const statusColors: Record<WorkflowDirection["status"], "neutral" | "primary" | "info" | "success"> = {
  draft: "neutral",
  registered: "primary",
  in_progress: "info",
  completed: "success",
};

const sampleStatusColors: Record<WorkflowSample["status"], "neutral" | "primary" | "info" | "success" | "error"> = {
  pending: "neutral",
  registered: "primary",
  analyzed: "info",
  completed: "success",
  rejected: "error",
};

const directionStatusLabels: Record<WorkflowDirection["status"], string> = {
  draft: "Черновик",
  registered: "Зарегистрировано",
  in_progress: "В работе",
  completed: "Завершено",
};

const sampleStatusLabels: Record<WorkflowSample["status"], string> = {
  pending: "Ожидает",
  registered: "Зарегистрирован",
  analyzed: "Проанализирован",
  completed: "Завершён",
  rejected: "Брак",
};

const directionTabs = computed<TabsItem[]>(() => [
  {
    label: "Образцы",
    icon: "i-lucide-vial",
    value: "samples",
  },
  {
    label: "История",
    icon: "i-lucide-history",
    value: "history",
  },
]);

const directionHistoryItems = computed<StepperItem[]>(() => {
  if (!selectedDirection.value) return [];

  const direction = selectedDirection.value;
  const items: StepperItem[] = [
    {
      title: "Создано направление",
      description: `${formatDate(direction.collectedAt)} · ${direction.doctor}\nОбъект и образцы внесены в направление.`,
      icon: "i-lucide-file-plus-2",
      value: 1,
    },
    {
      title: "Доставлено в приёмку",
      description: `${formatDate(direction.collectedAt)} · Регистратор\nОбразцы ожидают регистрации.`,
      icon: "i-lucide-truck",
      value: 2,
    },
  ];

  if (["registered", "in_progress", "completed"].includes(direction.status)) {
    items.push({
      title: "Образцы зарегистрированы",
      description: `${formatDate(direction.collectedAt)} · Регистратор\nНаправление передано в лаборатории.`,
      icon: "i-lucide-clipboard-check",
      value: 3,
    });
  }

  if (["in_progress", "completed"].includes(direction.status)) {
    items.push({
      title: "Лабораторная работа",
      description: `${formatDate(direction.deadline)} · Лаборатория\nИсследования выполняются по назначенным целям.`,
      icon: "i-lucide-flask-conical",
      value: 4,
    });
  }

  if (direction.status === "completed") {
    items.push({
      title: "Направление завершено",
      description: `${formatDate(direction.deadline)} · ${direction.protocol === "issued" ? "Протокол выпущен" : "Протокол готовится"}`,
      icon: "i-lucide-circle-check",
      value: 5,
    });
  }

  return items;
});

function formatDate(date: string) {
  return format(new Date(date), "dd.MM.yyyy HH:mm");
}

function selectDirection(direction: WorkflowDirection) {
  selectedDirection.value = direction;
  router.replace({ query: { ...route.query, id: String(direction.id) } });
}

function createDirection() {
  addDirection();
  selectedDirection.value = directions.value[0] ?? null;
  createOpen.value = false;
  toast.add({ title: "Направление создано", color: "success" });
}

function importDirection() {
  addDirection();
  selectedDirection.value = directions.value[0] ?? null;
  importOpen.value = false;
  toast.add({ title: "Импорт создан как draft", color: "success" });
}

function registerSelectedDirection() {
  if (!selectedDirection.value) return;
  registerDirection(selectedDirection.value);
  toast.add({ title: "Направление зарегистрировано", color: "success" });
}

function setSampleStatus(sample: WorkflowSample, status: WorkflowSample["status"]) {
  updateSample(sample, status);
  toast.add({ title: status === "rejected" ? "Образец отклонён" : "Образец принят", color: status === "rejected" ? "warning" : "success" });
}

function issueSelectedProtocol() {
  if (!selectedDirection.value) return;
  issueProtocol(selectedDirection.value);
  protocolOpen.value = false;
  toast.add({ title: "Протокол выпущен", color: "success" });
}

watch(() => route.query.id, (rawId) => {
  const id = typeof rawId === "string" ? Number(rawId) : Number.NaN;
  if (!Number.isFinite(id)) return;
  selectedDirection.value = directions.value.find((direction) => direction.id === id) ?? selectedDirection.value;
}, { immediate: true });

watch(selectedRoleKey, () => {
  selectedDirection.value = filteredDirections.value[0] ?? null;
});
</script>

<template>
  <UDashboardPanel
    id="directions-list"
    :default-size="32"
    :min-size="24"
    :max-size="42"
    resizable
  >
    <template #header>
      <UDashboardNavbar title="Направления">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>
        <template #right>
          <UBadge :label="selectedRole.shortName" color="primary" variant="subtle" />
          <UBadge :label="readonlyMode ? 'read-only' : 'editable'" color="neutral" variant="outline" />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <div class="flex w-full flex-col gap-3">
          <UFieldGroup class="w-full">
            <UInput
              v-model="query"
              icon="i-lucide-search"
              placeholder="Номер, объект, врач или филиал"
              class="min-w-0 flex-1"
            />
            <USelect
              v-model="selectedFilter"
              :items="filterItems"
              value-key="value"
              class="w-36"
            />
          </UFieldGroup>

          <div v-if="canEditDirections" class="flex gap-2">
            <UButton
              icon="i-lucide-upload"
              label="Импорт"
              color="primary"
              size="sm"
              @click="importOpen = true"
            />
            <UButton
              icon="i-lucide-plus"
              label="Создать"
              color="neutral"
              variant="outline"
              size="sm"
              @click="createOpen = true"
            />
          </div>
        </div>
      </UDashboardToolbar>
    </template>

    <div class="flex-1 overflow-y-auto divide-y divide-default">
      <button
        v-for="direction in filteredDirections"
        :key="direction.id"
        type="button"
        class="block w-full border-l-2 p-4 text-left transition-colors sm:px-6"
        :class="selectedDirection?.id === direction.id ? 'border-primary bg-primary/10' : 'border-transparent hover:border-primary hover:bg-primary/5'"
        @click="selectDirection(direction)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <p class="truncate text-sm font-semibold text-highlighted">
                {{ direction.number }}
              </p>
              <UBadge
                v-if="direction.urgency === 'urgent'"
                label="Срочно"
                color="warning"
                variant="subtle"
                size="xs"
              />
            </div>
            <p class="truncate text-sm text-toned">
              {{ direction.object }}
            </p>
            <p class="truncate text-xs text-muted">
              {{ direction.doctor }} · {{ direction.branch }}
            </p>
          </div>
          <UBadge :color="statusColors[direction.status]" :label="direction.status" variant="subtle" />
        </div>
        <div class="mt-3 flex items-center justify-between gap-2 text-xs text-muted">
          <span>{{ direction.samples.length }} образца</span>
          <span>{{ formatDate(direction.deadline) }}</span>
        </div>
      </button>

      <div v-if="!filteredDirections.length" class="p-10 text-center text-sm text-muted">
        Направления не найдены.
      </div>
    </div>
  </UDashboardPanel>

  <UDashboardPanel v-if="selectedDirection" id="directions-detail" class="hidden lg:flex">
    <template #header>
      <UDashboardNavbar :title="selectedDirection.number" :toggle="false">
        <template #right>
          <UBadge :color="statusColors[selectedDirection.status]" :label="selectedDirection.status" variant="subtle" />
        </template>
      </UDashboardNavbar>

      <div class="border-b border-default px-4 pt-5 sm:px-6">
        <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <UBadge
                :color="statusColors[selectedDirection.status]"
                variant="solid"
                size="sm"
                class="uppercase"
                :label="directionStatusLabels[selectedDirection.status]"
              />
              <span class="text-xs font-medium text-muted">
                ID: {{ selectedDirection.number }}
              </span>
            </div>

            <h2 class="mt-2 truncate text-2xl font-semibold text-highlighted">
              {{ selectedDirection.object }}
            </h2>

            <p class="mt-1 truncate text-sm text-muted">
              {{ selectedDirection.doctor }} · {{ selectedDirection.branch }}
            </p>

            <div class="mt-3 flex flex-wrap items-center gap-2">
              <UBadge
                color="neutral"
                variant="outline"
                :label="`Отбор: ${formatDate(selectedDirection.collectedAt)}`"
              />
              <UBadge
                color="neutral"
                variant="outline"
                :label="`Дедлайн: ${formatDate(selectedDirection.deadline)}`"
              />
              <UBadge
                :color="selectedDirection.protocol === 'missing' ? 'neutral' : 'success'"
                variant="subtle"
                :label="`Протокол: ${selectedDirection.protocol}`"
              />
            </div>
          </div>

          <div class="flex shrink-0 flex-wrap gap-2">
            <UButton
              icon="i-lucide-printer"
              label="Печать"
              color="neutral"
              variant="outline"
            />
            <UButton
              v-if="canEditDirections && selectedDirection.status === 'draft'"
              icon="i-lucide-clipboard-check"
              label="Зарегистрировать"
              color="primary"
              @click="registerSelectedDirection"
            />
            <UButton
              v-if="canSeeProtocol && selectedDirection.protocol !== 'missing'"
              icon="i-lucide-file-check-2"
              label="Протокол"
              color="neutral"
              variant="outline"
              @click="protocolOpen = true"
            />
          </div>
        </div>

        <UTabs
          v-model="activeDirectionTab"
          :items="directionTabs"
          variant="link"
          :content="false"
          class="mt-5"
        />
      </div>
    </template>

    <template #body>
      <div class="mx-auto flex w-full max-w-7xl flex-col gap-5">
        <div v-if="activeDirectionTab === 'samples'" class="flex min-w-0 flex-col gap-5">
          <section>
            <h2 class="mb-3 text-xl font-semibold text-highlighted">
              Направление
            </h2>

            <div class="overflow-hidden rounded-lg border border-default">
              <dl class="grid text-sm sm:grid-cols-2">
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Номер
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ selectedDirection.number }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Год
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ new Date(selectedDirection.collectedAt).getFullYear() }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Время отбора
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ formatDate(selectedDirection.collectedAt) }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Время доставки
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ formatDate(selectedDirection.collectedAt) }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Санитарный врач
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ selectedDirection.doctor }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Объект
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ selectedDirection.object }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Статус
                  </dt>
                  <dd class="px-3 py-2">
                    <UBadge
                      :color="statusColors[selectedDirection.status]"
                      :label="directionStatusLabels[selectedDirection.status]"
                      variant="subtle"
                    />
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Завершено
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ selectedDirection.status === 'completed' ? 'Да' : 'Нет' }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] sm:border-e">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Время выпуска
                  </dt>
                  <dd class="px-3 py-2 text-muted">
                    {{ selectedDirection.protocol === 'issued' ? formatDate(selectedDirection.deadline) : 'Не выпущено' }}
                  </dd>
                </div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)]">
                  <dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">
                    Протокол
                  </dt>
                  <dd class="px-3 py-2">
                    <UBadge
                      :color="selectedDirection.protocol === 'missing' ? 'neutral' : 'success'"
                      :label="selectedDirection.protocol"
                      variant="subtle"
                    />
                  </dd>
                </div>
              </dl>
            </div>
          </section>

          <section>
            <div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-vial" class="size-4 text-muted" />
                <h3 class="text-sm font-semibold text-highlighted">
                  Зарегистрированные образцы для направления
                </h3>
              </div>
              <UBadge
                :label="`${selectedDirection.samples.length} образца`"
                color="neutral"
                variant="subtle"
              />
            </div>

            <div class="overflow-x-auto rounded-lg border border-default">
              <table class="min-w-[980px] w-full border-collapse text-sm">
                <thead class="bg-elevated text-left text-xs font-medium uppercase text-muted">
                  <tr>
                    <th class="border-b border-default px-3 py-2">
                      №
                    </th>
                    <th class="border-b border-default px-3 py-2">
                      Тип образца
                    </th>
                    <th class="border-b border-default px-3 py-2">
                      Наименование
                    </th>
                    <th class="border-b border-default px-3 py-2">
                      Цель исследования
                    </th>
                    <th class="border-b border-default px-3 py-2">
                      Завершено
                    </th>
                    <th class="border-b border-default px-3 py-2">
                      Результат
                    </th>
                    <th class="border-b border-default px-3 py-2">
                      Время выпуска
                    </th>
                    <th class="border-b border-default px-3 py-2 text-right">
                      Действия
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="sample in selectedDirection.samples"
                    :key="sample.id"
                    class="border-b border-default last:border-b-0 odd:bg-elevated/35"
                  >
                    <td class="px-3 py-2 align-top font-mono text-xs text-muted">
                      {{ sample.code }}
                    </td>
                    <td class="px-3 py-2 align-top text-muted">
                      {{ sample.type }}
                    </td>
                    <td class="px-3 py-2 align-top">
                      <p class="font-medium text-highlighted">
                        {{ selectedDirection.object }}
                      </p>
                      <p class="text-xs text-muted">
                        {{ sample.lab }}
                      </p>
                    </td>
                    <td class="px-3 py-2 align-top text-muted">
                      {{ sample.lab }}
                    </td>
                    <td class="px-3 py-2 align-top text-muted">
                      {{ ['completed', 'rejected'].includes(sample.status) ? 'Да' : 'Нет' }}
                    </td>
                    <td class="px-3 py-2 align-top">
                      <UBadge
                        :color="sampleStatusColors[sample.status]"
                        :label="sampleStatusLabels[sample.status]"
                        variant="subtle"
                      />
                    </td>
                    <td class="px-3 py-2 align-top text-muted">
                      {{ formatDate(sample.deadline) }}
                    </td>
                    <td class="px-3 py-2 align-top">
                      <div class="flex justify-end gap-1">
                        <UButton
                          icon="i-lucide-search"
                          color="neutral"
                          variant="ghost"
                          size="sm"
                        />
                        <UButton
                          v-if="canEditDirections && sample.status === 'pending'"
                          icon="i-lucide-check"
                          color="primary"
                          variant="ghost"
                          size="sm"
                          @click="setSampleStatus(sample, 'registered')"
                        />
                        <UButton
                          v-if="canEditDirections && sample.status === 'pending'"
                          icon="i-lucide-x"
                          color="error"
                          variant="ghost"
                          size="sm"
                          @click="setSampleStatus(sample, 'rejected')"
                        />
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <section v-else class="rounded-lg border border-default p-4">
          <div class="mb-3 flex items-center gap-2">
            <UIcon name="i-lucide-history" class="size-4 text-muted" />
            <h3 class="text-sm font-semibold text-highlighted">
              История направления
            </h3>
          </div>

          <UStepper
            orientation="vertical"
            :items="directionHistoryItems"
            :default-value="directionHistoryItems.length"
            disabled
            class="w-full"
            :ui="{
              item: 'items-start',
              title: 'text-sm font-semibold text-highlighted',
              description: 'whitespace-pre-line text-xs leading-5 text-muted',
              separator: 'min-h-8'
            }"
          />
        </section>
      </div>
    </template>
  </UDashboardPanel>

  <div v-else class="hidden flex-1 flex-col items-center justify-center gap-3 lg:flex">
    <UIcon name="i-lucide-book-copy" class="size-28 text-dimmed" />
    <p class="text-sm text-muted">
      Выберите направление.
    </p>
  </div>

  <UModal v-model:open="importOpen" title="Импорт направления" description="Файл будет разобран в preview, затем создан draft.">
    <template #body>
      <UFileUpload label="Загрузить файл направления" description="PDF, XLSX или XML" class="w-full" />
    </template>
    <template #footer>
      <UButton
        label="Отмена"
        color="neutral"
        variant="ghost"
        @click="importOpen = false"
      />
      <UButton label="Создать draft" icon="i-lucide-upload" @click="importDirection" />
    </template>
  </UModal>

  <UModal v-model:open="createOpen" title="Создание направления" description="V1 создаёт mock draft, совместимый с будущим API.">
    <template #body>
      <div class="grid gap-3 sm:grid-cols-2">
        <UInput model-value="Новый объект" placeholder="Объект" />
        <UInput model-value="Анна Смирнова" placeholder="Врач" />
        <UInput model-value="Смыв" placeholder="Тип образца" />
        <USelect model-value="normal" :items="[{ label: 'Обычная', value: 'normal' }, { label: 'Срочная', value: 'urgent' }]" value-key="value" />
      </div>
    </template>
    <template #footer>
      <UButton
        label="Отмена"
        color="neutral"
        variant="ghost"
        @click="createOpen = false"
      />
      <UButton label="Создать" icon="i-lucide-plus" @click="createDirection" />
    </template>
  </UModal>

  <UModal v-model:open="protocolOpen" title="Протокол" description="Закрытые образцы собраны в протокол с заключением.">
    <template #body>
      <UTextarea model-value="Заключение: показатели в пределах допустимых значений." autoresize class="w-full" />
    </template>
    <template #footer>
      <UButton
        label="Закрыть"
        color="neutral"
        variant="ghost"
        @click="protocolOpen = false"
      />
      <UButton
        v-if="canEditDirections && selectedDirection?.protocol !== 'issued'"
        label="Выпустить"
        icon="i-lucide-file-check-2"
        @click="issueSelectedProtocol"
      />
    </template>
  </UModal>
</template>
