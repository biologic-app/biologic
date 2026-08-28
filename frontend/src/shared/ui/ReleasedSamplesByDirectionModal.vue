<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useToast } from "@nuxt/ui/composables";
import { useAuth } from "@/modules/auth";
import { apiRequest } from "@/shared/api/client.api";

// Модалка «Выпущенные образцы по направлениям» — открывается со страниц
// «Образцы» и «Направления». Показывает завершённые (выпущенные) образцы,
// сгруппированные по направлениям; если все образцы направления выпущены,
// карточка подсвечивается жёлтым. По группе — «Создать протокол».
const open = defineModel<boolean>("open", { default: false });

interface ReleasedSampleItem {
  id: string;
  name: string | null;
  status_code: string | null;
  status_name: string | null;
  sample_type_name: string | null;
  protocol_id: string | null;
  completed_at: string | null;
}

interface ReleasedDirectionInfo {
  id: string;
  year_no: number | null;
  base_no: number | null;
  doctor: string | null;
  object: { name: string | null; code: string | null };
}

interface ReleasedDirectionGroup {
  direction: ReleasedDirectionInfo;
  samples: ReleasedSampleItem[];
  released_count: number;
  total_count: number;
  all_released: boolean;
}

const SAMPLE_COMPLETED = "completed";

const { t } = useI18n();
const toast = useToast();
const auth = useAuth();

const groups = ref<ReleasedDirectionGroup[]>([]);
const isLoading = ref(false);
const errorMessage = ref<string | null>(null);
const creatingDirectionId = ref<string | null>(null);

const canCreateProtocol = computed(() => auth.can("protocols", "create"));

const resolveErrorMessage = (error: unknown) => {
  if (error instanceof Error) {
    return error.message;
  }
  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof (error as { message: unknown }).message === "string"
  ) {
    return (error as { message: string }).message;
  }
  return t("releasedSamples.loadError");
};

const directionNumber = (group: ReleasedDirectionGroup) => {
  const { year_no, base_no } = group.direction;
  if (year_no == null && base_no == null) {
    return "—";
  }
  return `${year_no ?? "—"}/${base_no ?? "—"}`;
};

const releasableSampleIds = (group: ReleasedDirectionGroup) =>
  group.samples
    .filter((sample) => sample.status_code === SAMPLE_COMPLETED && !sample.protocol_id)
    .map((sample) => sample.id);

const canCreateForGroup = (group: ReleasedDirectionGroup) =>
  canCreateProtocol.value && releasableSampleIds(group).length > 0;

const sampleStatusColor = (statusCode: string | null) => {
  switch (statusCode) {
    case "completed":
      return "success" as const;
    case "rejected":
      return "error" as const;
    case "analyzed":
      return "info" as const;
    case "in_progress":
      return "warning" as const;
    default:
      return "neutral" as const;
  }
};

const load = async () => {
  isLoading.value = true;
  errorMessage.value = null;
  try {
    const response = await apiRequest<{ data: ReleasedDirectionGroup[] }>(
      "/directions/released-samples",
    );
    groups.value = response.data ?? [];
  } catch (error: unknown) {
    errorMessage.value = resolveErrorMessage(error);
    groups.value = [];
  } finally {
    isLoading.value = false;
  }
};

const createProtocol = async (group: ReleasedDirectionGroup) => {
  const actorId = auth.user?.id;
  const sampleIds = releasableSampleIds(group);
  if (!actorId || sampleIds.length === 0 || !canCreateProtocol.value) {
    return;
  }

  creatingDirectionId.value = group.direction.id;
  try {
    await apiRequest("/protocols", {
      method: "POST",
      body: {
        sample_ids: sampleIds,
      },
    });
    toast.add({
      title: t("releasedSamples.protocolCreated"),
      description: t("releasedSamples.protocolCreatedFor", {
        number: directionNumber(group),
        count: sampleIds.length,
      }),
      color: "success",
      icon: "i-lucide-circle-check",
    });
    await load();
  } catch (error: unknown) {
    toast.add({
      title: t("releasedSamples.protocolError"),
      description: resolveErrorMessage(error),
      color: "error",
      icon: "i-lucide-circle-alert",
    });
  } finally {
    creatingDirectionId.value = null;
  }
};

// Загружаем данные каждый раз при открытии модалки.
watch(open, (isOpen) => {
  if (isOpen) {
    load();
  }
});
</script>

<template>
  <UModal
    v-model:open="open"
    :title="t('nav.releasedSamples')"
    :description="t('releasedSamples.subtitle')"
    :ui="{ content: 'max-w-3xl' }"
  >
    <template #body>
      <div class="space-y-4">
        <div class="flex items-center justify-end">
          <UButton
            color="neutral"
            variant="ghost"
            icon="i-lucide-refresh-cw"
            :loading="isLoading"
            :label="t('releasedSamples.refresh')"
            @click="load"
          />
        </div>

        <UAlert
          v-if="errorMessage"
          color="error"
          variant="subtle"
          icon="i-lucide-circle-alert"
          :title="t('releasedSamples.loadError')"
          :description="errorMessage"
        />

        <div
          v-if="!isLoading && groups.length === 0 && !errorMessage"
          class="py-12 text-center text-sm text-muted"
        >
          {{ t("releasedSamples.empty") }}
        </div>

        <UCard
          v-for="group in groups"
          :key="group.direction.id"
          :class="[
            'transition-colors',
            group.all_released ? 'bg-warning/10 ring-2 ring-warning' : '',
          ]"
          data-telemetry="released-samples-direction-group"
        >
          <template #header>
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="min-w-0 space-y-1">
                <div class="flex items-center gap-2">
                  <UIcon name="i-lucide-book-copy" class="size-4 shrink-0 text-muted" />
                  <span class="font-semibold">№ {{ directionNumber(group) }}</span>
                  <UBadge
                    :color="group.all_released ? 'warning' : 'neutral'"
                    variant="subtle"
                    :label="`${group.released_count}/${group.total_count}`"
                  />
                  <UBadge
                    v-if="group.all_released"
                    color="warning"
                    variant="solid"
                    icon="i-lucide-package-check"
                    :label="t('releasedSamples.allReleased')"
                  />
                </div>
                <div class="text-sm text-muted">
                  <span v-if="group.direction.doctor">{{ group.direction.doctor }}</span>
                  <span v-if="group.direction.object?.name">
                    · {{ group.direction.object.name }}
                    <span v-if="group.direction.object?.code">
                      ({{ group.direction.object.code }})
                    </span>
                  </span>
                </div>
              </div>

              <UButton
                color="primary"
                icon="i-lucide-file-check-2"
                data-testid="create-protocol-for-direction"
                data-telemetry="released-samples-create-protocol"
                :label="t('releasedSamples.createProtocol')"
                :disabled="!canCreateForGroup(group)"
                :loading="creatingDirectionId === group.direction.id"
                @click="createProtocol(group)"
              />
            </div>
          </template>

          <ul class="divide-y divide-default">
            <li
              v-for="sample in group.samples"
              :key="sample.id"
              class="flex flex-wrap items-center justify-between gap-2 py-2"
            >
              <div class="min-w-0">
                <span class="font-medium">{{ sample.name || "—" }}</span>
                <span v-if="sample.sample_type_name" class="ml-2 text-sm text-muted">
                  {{ sample.sample_type_name }}
                </span>
              </div>
              <div class="flex items-center gap-2">
                <UBadge
                  v-if="sample.protocol_id"
                  color="neutral"
                  variant="outline"
                  icon="i-lucide-file-check-2"
                  :label="t('releasedSamples.inProtocol')"
                />
                <UBadge
                  :color="sampleStatusColor(sample.status_code)"
                  variant="subtle"
                  :label="sample.status_name || sample.status_code || '—'"
                />
              </div>
            </li>
          </ul>
        </UCard>
      </div>
    </template>
  </UModal>
</template>
