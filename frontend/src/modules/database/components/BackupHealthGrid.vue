<script setup lang="ts">
// Годовая полоса «хелсчеков»: одна ячейка — один день, зелёная если в этот день
// был успешный бэкап, красная при ошибке, нейтральная — бэкапов не было.
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type { DatabaseBackup } from "@/modules/database/types";

const props = defineProps<{ backups: DatabaseBackup[] }>();

const { t, locale } = useI18n();
const currentYear = new Date().getFullYear();

type DayStatus = "completed" | "failed" | "none";

interface DayCell {
  key: string;
  status: DayStatus;
  backups: DatabaseBackup[];
}

const STATUS_CLASS: Record<DayStatus, string> = {
  completed: "bg-success",
  failed: "bg-error",
  none: "bg-elevated border border-default",
};

function dayKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDate(value: string | Date): string {
  const date = typeof value === "string" ? new Date(`${value}T00:00:00`) : value;
  return new Intl.DateTimeFormat(locale.value === "ru" ? "ru-RU" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(locale.value === "ru" ? "ru-RU" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

const cells = computed<DayCell[]>(() => {
  const byDay = new Map<string, DatabaseBackup[]>();
  for (const backup of props.backups) {
    const key = dayKey(new Date(backup.createdAt));
    const list = byDay.get(key);
    if (list) {
      list.push(backup);
    } else {
      byDay.set(key, [backup]);
    }
  }

  const start = new Date(currentYear, 0, 1);
  const end = new Date(currentYear, 11, 31);

  const result: DayCell[] = [];
  for (const date = new Date(start); date <= end; date.setDate(date.getDate() + 1)) {
    const key = dayKey(date);
    const dayBackups = byDay.get(key) ?? [];
    const status: DayStatus = dayBackups.some((backup) => backup.status === "failed")
      ? "failed"
      : dayBackups.some((backup) => backup.status === "completed")
        ? "completed"
        : "none";
    result.push({ key, status, backups: dayBackups });
  }
  return result;
});

function tooltipText(cell: DayCell): string {
  if (cell.backups.length === 0) {
    return t("dataOperations.health.noBackup", { date: formatDate(cell.key) });
  }
  return cell.backups
    .map((backup) => {
      const status = backup.status === "failed" ? ` (${t("dataOperations.health.failed")})` : "";
      return `${formatDateTime(backup.createdAt)}${status}`;
    })
    .join(", ");
}
</script>

<template>
  <div class="flex flex-wrap gap-0.5" :aria-label="t('dataOperations.health.title')">
    <UTooltip
      v-for="cell in cells"
      :key="cell.key"
      :content="{ side: 'top', align: 'center', sideOffset: 3 }"
      :ui="{ content: 'w-max max-w-none h-auto' }"
      arrow
    >
      <span
        class="size-4 rounded-[2px]"
        :class="STATUS_CLASS[cell.status]"
        tabindex="0"
        :aria-label="tooltipText(cell)"
      />
      <template #content>
        <p v-if="cell.backups.length === 0" class="w-max max-w-none text-xs whitespace-nowrap">
          {{ t("dataOperations.health.noBackup", { date: formatDate(cell.key) }) }}
        </p>
        <ul v-else class="w-max max-w-none space-y-1 text-xs whitespace-nowrap">
          <li v-for="backup in cell.backups" :key="backup.id" class="flex items-center gap-2">
            <span>{{ formatDateTime(backup.createdAt) }}</span>
            <span v-if="backup.status === 'failed'" class="text-error">
              ({{ t("dataOperations.health.failed") }})
            </span>
          </li>
        </ul>
      </template>
    </UTooltip>
  </div>
</template>
