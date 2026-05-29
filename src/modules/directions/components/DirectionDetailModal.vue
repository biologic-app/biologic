<script setup lang="ts">
import { format } from "date-fns";
import { computed, ref } from "vue";
import type { StepperItem, TabsItem } from "@nuxt/ui";

interface DirectionSample {
  id: number;
  code: string;
  type: string;
  lab: string;
  status: "pending" | "registered" | "analyzed" | "completed" | "rejected";
  deadline: string;
}

interface Direction {
  id: number;
  number: string;
  object: string;
  doctor: string;
  branch: string;
  status: "draft" | "registered" | "in_progress" | "completed";
  urgency: "normal" | "urgent";
  protocol: "missing" | "draft" | "issued";
  collectedAt: string;
  deadline: string;
  samples: DirectionSample[];
}

const props = defineProps<{
  open: boolean;
  direction: Direction | null;
}>();

const emit = defineEmits<{
  (e: "update:open", value: boolean): void;
  (e: "register"): void;
  (e: "protocol"): void;
  (e: "sampleAction", sample: DirectionSample, action: "accept" | "reject"): void;
}>();

const activeTab = ref<"samples" | "history">("samples");

const statusColors: Record<string, "neutral" | "primary" | "info" | "success"> = {
  draft: "neutral", registered: "primary", in_progress: "info", completed: "success",
};

const sampleStatusColors: Record<string, "neutral" | "primary" | "info" | "success" | "error"> = {
  pending: "neutral", registered: "primary", analyzed: "info", completed: "success", rejected: "error",
};

const directionStatusLabels: Record<string, string> = {
  draft: "Черновик", registered: "Зарегистрировано", in_progress: "В работе", completed: "Завершено",
};

const sampleStatusLabels: Record<string, string> = {
  pending: "Ожидает", registered: "Зарегистрирован", analyzed: "Проанализирован", completed: "Завершён", rejected: "Брак",
};

function formatDate(date: string) {
  return format(new Date(date), "dd.MM.yyyy HH:mm");
}

const directionTabs = computed<TabsItem[]>(() => [
  { label: "Образцы", icon: "i-lucide-test-tube-2", value: "samples" },
  { label: "История", icon: "i-lucide-history", value: "history" },
]);

const directionHistoryItems = computed<StepperItem[]>(() => {
  if (!props.direction) return [];
  const direction = props.direction;
  const items: StepperItem[] = [
    { title: "Создано направление", description: `${formatDate(direction.collectedAt)} · ${direction.doctor}\nОбъект и образцы внесены в направление.`, icon: "i-lucide-file-plus-2", value: 1 },
    { title: "Доставлено в приёмку", description: `${formatDate(direction.collectedAt)} · Регистратор\nОбразцы ожидают регистрации.`, icon: "i-lucide-truck", value: 2 },
  ];
  if (["registered", "in_progress", "completed"].includes(direction.status)) {
    items.push({ title: "Образцы зарегистрированы", description: `${formatDate(direction.collectedAt)} · Регистратор\nНаправление передано в лаборатории.`, icon: "i-lucide-clipboard-check", value: 3 });
  }
  if (["in_progress", "completed"].includes(direction.status)) {
    items.push({ title: "Лабораторная работа", description: `${formatDate(direction.deadline)} · Лаборатория\nИсследования выполняются по назначенным целям.`, icon: "i-lucide-flask-conical", value: 4 });
  }
  if (direction.status === "completed") {
    items.push({ title: "Направление завершено", description: `${formatDate(direction.deadline)} · ${direction.protocol === "issued" ? "Протокол выпущен" : "Протокол готовится"}`, icon: "i-lucide-circle-check", value: 5 });
  }
  return items;
});
</script>

<template>
  <UModal
    :open="open"
    :ui="{ content: 'max-w-6xl' }"
    @update:open="emit('update:open', $event)"
  >
    <template #header>
      <div v-if="direction" class="flex items-center gap-3">
        <span class="font-semibold text-highlighted">{{ direction.number }}</span>
        <UBadge :color="statusColors[direction.status]" :label="directionStatusLabels[direction.status]" variant="subtle" />
      </div>
    </template>

    <template #body>
      <div v-if="direction" class="flex flex-col gap-5">
        <!-- Header -->
        <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <UBadge :color="statusColors[direction.status]" variant="solid" size="sm" class="uppercase" :label="directionStatusLabels[direction.status]" />
              <span class="text-xs font-medium text-muted">ID: {{ direction.number }}</span>
            </div>
            <h2 class="mt-2 truncate text-2xl font-semibold text-highlighted">{{ direction.object }}</h2>
            <p class="mt-1 truncate text-sm text-muted">{{ direction.doctor }} · {{ direction.branch }}</p>
            <div class="mt-3 flex flex-wrap items-center gap-2">
              <UBadge color="neutral" variant="outline" :label="`Отбор: ${formatDate(direction.collectedAt)}`" />
              <UBadge color="neutral" variant="outline" :label="`Дедлайн: ${formatDate(direction.deadline)}`" />
              <UBadge :color="direction.protocol === 'missing' ? 'neutral' : 'success'" variant="subtle" :label="`Протокол: ${direction.protocol}`" />
            </div>
          </div>
          <div class="flex shrink-0 flex-wrap gap-2">
            <UButton icon="i-lucide-printer" label="Печать" color="neutral" variant="outline" />
            <UButton v-if="direction.status === 'draft'" icon="i-lucide-clipboard-check" label="Зарегистрировать" color="primary" @click="emit('register')" />
            <UButton v-if="direction.protocol !== 'missing'" icon="i-lucide-file-check-2" label="Протокол" color="neutral" variant="outline" @click="emit('protocol')" />
          </div>
        </div>

        <UTabs v-model="activeTab" :items="directionTabs" variant="link" :content="false" />

        <!-- Samples tab -->
        <div v-if="activeTab === 'samples'" class="flex min-w-0 flex-col gap-5">
          <section>
            <h2 class="mb-3 text-xl font-semibold text-highlighted">Направление</h2>
            <div class="overflow-hidden rounded-lg border border-default">
              <dl class="grid text-sm sm:grid-cols-2">
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e"><dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">Номер</dt><dd class="px-3 py-2 text-muted">{{ direction.number }}</dd></div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default"><dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">Год</dt><dd class="px-3 py-2 text-muted">{{ new Date(direction.collectedAt).getFullYear() }}</dd></div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e"><dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">Время отбора</dt><dd class="px-3 py-2 text-muted">{{ formatDate(direction.collectedAt) }}</dd></div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default"><dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">Время доставки</dt><dd class="px-3 py-2 text-muted">{{ formatDate(direction.collectedAt) }}</dd></div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e"><dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">Санитарный врач</dt><dd class="px-3 py-2 text-muted">{{ direction.doctor }}</dd></div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default"><dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">Объект</dt><dd class="px-3 py-2 text-muted">{{ direction.object }}</dd></div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default sm:border-e"><dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">Статус</dt><dd class="px-3 py-2"><UBadge :color="statusColors[direction.status]" :label="directionStatusLabels[direction.status]" variant="subtle" /></dd></div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] border-b border-default"><dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">Завершено</dt><dd class="px-3 py-2 text-muted">{{ direction.status === 'completed' ? 'Да' : 'Нет' }}</dd></div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)] sm:border-e"><dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">Время выпуска</dt><dd class="px-3 py-2 text-muted">{{ direction.protocol === 'issued' ? formatDate(direction.deadline) : 'Не выпущено' }}</dd></div>
                <div class="grid grid-cols-[10rem_minmax(0,1fr)]"><dt class="bg-elevated/60 px-3 py-2 font-medium text-highlighted">Протокол</dt><dd class="px-3 py-2"><UBadge :color="direction.protocol === 'missing' ? 'neutral' : 'success'" :label="direction.protocol" variant="subtle" /></dd></div>
              </dl>
            </div>
          </section>

          <section>
            <div class="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div class="flex items-center gap-2"><UIcon name="i-lucide-test-tube-2" class="size-4 text-muted" /><h3 class="text-sm font-semibold text-highlighted">Зарегистрированные образцы для направления</h3></div>
              <UBadge :label="`${direction.samples.length} образца`" color="neutral" variant="subtle" />
            </div>
            <div class="overflow-x-auto rounded-lg border border-default">
              <table class="min-w-[980px] w-full border-collapse text-sm">
                <thead class="bg-elevated text-left text-xs font-medium uppercase text-muted">
                  <tr>
                    <th class="border-b border-default px-3 py-2">№</th><th class="border-b border-default px-3 py-2">Тип образца</th><th class="border-b border-default px-3 py-2">Наименование</th><th class="border-b border-default px-3 py-2">Цель исследования</th><th class="border-b border-default px-3 py-2">Завершено</th><th class="border-b border-default px-3 py-2">Результат</th><th class="border-b border-default px-3 py-2">Время выпуска</th><th class="border-b border-default px-3 py-2 text-right">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="sample in direction.samples" :key="sample.id" class="border-b border-default last:border-b-0 odd:bg-elevated/35">
                    <td class="px-3 py-2 align-top font-mono text-xs text-muted">{{ sample.code }}</td>
                    <td class="px-3 py-2 align-top text-muted">{{ sample.type }}</td>
                    <td class="px-3 py-2 align-top"><p class="font-medium text-highlighted">{{ direction.object }}</p><p class="text-xs text-muted">{{ sample.lab }}</p></td>
                    <td class="px-3 py-2 align-top text-muted">{{ sample.lab }}</td>
                    <td class="px-3 py-2 align-top text-muted">{{ ['completed', 'rejected'].includes(sample.status) ? 'Да' : 'Нет' }}</td>
                    <td class="px-3 py-2 align-top"><UBadge :color="sampleStatusColors[sample.status]" :label="sampleStatusLabels[sample.status]" variant="subtle" /></td>
                    <td class="px-3 py-2 align-top text-muted">{{ formatDate(sample.deadline) }}</td>
                    <td class="px-3 py-2 align-top">
                      <div class="flex justify-end gap-1">
                        <UButton icon="i-lucide-search" color="neutral" variant="ghost" size="sm" />
                        <UButton v-if="sample.status === 'pending'" icon="i-lucide-check" color="primary" variant="ghost" size="sm" @click="emit('sampleAction', sample, 'accept')" />
                        <UButton v-if="sample.status === 'pending'" icon="i-lucide-x" color="error" variant="ghost" size="sm" @click="emit('sampleAction', sample, 'reject')" />
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- History tab -->
        <section v-else class="rounded-lg border border-default p-4">
          <div class="mb-3 flex items-center gap-2"><UIcon name="i-lucide-history" class="size-4 text-muted" /><h3 class="text-sm font-semibold text-highlighted">История направления</h3></div>
          <UStepper orientation="vertical" :items="directionHistoryItems" :default-value="directionHistoryItems.length" disabled class="w-full" :ui="{ item: 'items-start', title: 'text-sm font-semibold text-highlighted', description: 'whitespace-pre-line text-xs leading-5 text-muted', separator: 'min-h-8' }" />
        </section>
      </div>
    </template>

    <template #footer>
      <UButton label="Закрыть" color="neutral" variant="ghost" @click="emit('update:open', false)" />
    </template>
  </UModal>
</template>
