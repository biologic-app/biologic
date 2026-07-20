<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { CrudRow } from "@/shared/types/crud";
import { apiReadRequest } from "@/shared/api/client.api";
import { sampleRecordCode } from "@/shared/ui/entity-detail.helpers";

const props = defineProps<{
  open: boolean;
  protocol: CrudRow | null;
  samples: CrudRow[];
}>();

const emit = defineEmits<{
  (e: "update:open", value: boolean): void;
}>();

interface ConclusionText {
  name: string;
  text_singular: string | null;
  text_plural: string | null;
}

interface DirectionInfo {
  base_no: number | null;
  year_no: number;
  doctor_id: string | null;
  object_id: string | null;
  received_at: string | null;
}

interface DoctorInfo {
  first_name: string;
  last_name: string | null;
  patronymic: string | null;
}

interface ObjectInfo {
  name: string;
}

const conclusionText = ref<ConclusionText | null>(null);
const conclusionLoading = ref(false);
const directionInfo = ref<DirectionInfo | null>(null);
const doctorName = ref<string | null>(null);
const objectName = ref<string | null>(null);
const headerLoading = ref(false);

// The list/detail responses may already carry a resolved `conclusion`
// relation (name only), but the preview needs the document text
// (text_singular/text_plural) — fetched directly so the preview doesn't
// depend on which include path happened to populate the row.
watch(
  () => [props.open, props.protocol?.conclusion_id] as const,
  async ([open, conclusionId]) => {
    conclusionText.value = null;
    if (!open || !conclusionId) return;
    conclusionLoading.value = true;
    try {
      const response = await apiReadRequest<ConclusionText>(`/conclusions/${conclusionId}`);
      conclusionText.value = response.data;
    } catch {
      conclusionText.value = null;
    } finally {
      conclusionLoading.value = false;
    }
  },
  { immediate: true },
);

// "По направлению"/"Объект" come from the parent direction, reached
// through the first sample — samples list/read responses don't carry a
// populated `direction`/`doctor`/`object` relation object (only `status`
// is actually wired up server-side, see _populate_sample_includes), so
// this fetches the raw ids directly and resolves doctor/object by hand.
watch(
  () => [props.open, props.samples[0]?.direction_id] as const,
  async ([open, directionId]) => {
    directionInfo.value = null;
    doctorName.value = null;
    objectName.value = null;
    if (!open || !directionId) return;
    headerLoading.value = true;
    try {
      const direction = await apiReadRequest<DirectionInfo>(`/directions/${directionId}`);
      directionInfo.value = direction.data;

      const [doctor, object] = await Promise.all([
        direction.data.doctor_id
          ? apiReadRequest<DoctorInfo>(`/doctors/${direction.data.doctor_id}`).catch(() => null)
          : Promise.resolve(null),
        direction.data.object_id
          ? apiReadRequest<ObjectInfo>(`/objects/${direction.data.object_id}`).catch(() => null)
          : Promise.resolve(null),
      ]);
      if (doctor) {
        const { first_name, last_name, patronymic } = doctor.data;
        const initials = [first_name, patronymic]
          .filter(Boolean)
          .map((part) => `${(part as string)[0]}.`)
          .join("");
        doctorName.value = [last_name, initials].filter(Boolean).join(" ") || null;
      }
      if (object) {
        objectName.value = object.data.name || null;
      }
    } catch {
      directionInfo.value = null;
    } finally {
      headerLoading.value = false;
    }
  },
  { immediate: true },
);

function formatRuDateQuoted(value: string | null | undefined) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const parts = new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).formatToParts(date);
  const day = parts.find((part) => part.type === "day")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  const year = parts.find((part) => part.type === "year")?.value;
  if (!day || !month || !year) return null;
  return `«${day}» ${month} ${year} г.`;
}

function formatShortDate(value: unknown) {
  if (typeof value !== "string" || !value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}

function registrationNumber(sample: CrudRow, index: number) {
  return sampleRecordCode(sample) ?? String(index + 1);
}

const issuedDateLine = computed(
  () => formatRuDateQuoted((props.protocol?.issued_at ?? props.protocol?.created_at) as string) ?? "",
);

const receivedDateLine = computed(() => formatRuDateQuoted(directionInfo.value?.received_at));

const directionReference = computed(() => {
  const info = directionInfo.value;
  if (!info) return null;
  return info.base_no ? `№ ${info.base_no}/${info.year_no}` : `№ ${info.year_no}`;
});

const referrerLine = computed(() => doctorName.value || directionReference.value || "—");
const objectLine = computed(() => objectName.value || "—");

const sampleNotes = computed(() =>
  props.samples
    .map((sample, index) => ({
      regNumber: registrationNumber(sample, index),
      comment: (sample.comment ?? sample.target_description) as string | null,
    }))
    .filter((entry): entry is { regNumber: string; comment: string } => Boolean(entry.comment)),
);

const conclusionParagraph = computed(() => {
  const text = conclusionText.value;
  if (!text) return "заключение не указано.";
  const plural = props.samples.length !== 1;
  return (plural ? text.text_plural : text.text_singular) || text.name || "заключение не указано.";
});

const documentTitle = computed(() => {
  const yearNo = props.protocol?.year_no;
  return yearNo ? `ПРОТОКОЛ ЛАБОРАТОРНЫХ ИСПЫТАНИЙ № ${yearNo}` : "ПРОТОКОЛ ЛАБОРАТОРНЫХ ИСПЫТАНИЙ";
});

function close() {
  emit("update:open", false);
}
</script>

<template>
  <UModal
    :open="open"
    title="Предпросмотр протокола"
    :ui="{ content: 'w-[calc(100vw-2rem)] max-w-[54rem]' }"
    @update:open="emit('update:open', $event)"
  >
    <template #body>
      <div class="space-y-4">
        <div class="flex items-start gap-2 rounded-lg border border-dashed border-default bg-elevated/50 px-3 py-2 text-xs text-muted">
          <UIcon name="i-lucide-info" class="mt-0.5 size-4 shrink-0" />
          <span>
            Черновой предпросмотр на стороне фронтенда. Официальный документ будет
            формироваться на бэкенде по заранее подготовленному Excel-шаблону при экспорте.
          </span>
        </div>

        <div
          class="mx-auto max-w-[46rem] rounded-sm border border-default bg-white px-10 py-8 text-[13px] leading-6 text-neutral-900 shadow-sm"
          style="font-family: 'Times New Roman', Georgia, serif"
        >
          <p class="mb-1 text-right text-[11px] text-neutral-500">Для внутреннего пользования</p>
          <p class="mb-3 text-right text-[13px]">{{ issuedDateLine }}</p>

          <h2 class="mb-1 text-center text-[15px] font-bold uppercase">
            {{ documentTitle }}
          </h2>
          <p class="mb-4 text-center text-[12px] text-neutral-700">
            проб образцов, поступивших в лабораторию{{ receivedDateLine ? ` ${receivedDateLine}` : "" }}
          </p>

          <div class="mb-1 flex justify-center gap-2">
            <span class="text-right" style="flex: 0 0 40%">По направлению:</span>
            <span class="text-left" style="flex: 1 1 40%">
              <USkeleton v-if="headerLoading" class="inline-block h-4 w-32 align-middle" />
              <template v-else>{{ referrerLine }}</template>
            </span>
          </div>
          <div class="mb-4 flex justify-center gap-2">
            <span class="text-right" style="flex: 0 0 40%">Объект:</span>
            <span class="text-left" style="flex: 1 1 40%">
              <USkeleton v-if="headerLoading" class="inline-block h-4 w-32 align-middle" />
              <template v-else>{{ objectLine }}</template>
            </span>
          </div>

          <table class="mb-4 w-full border-collapse text-[12px]">
            <thead>
              <tr>
                <th class="border border-neutral-800 px-2 py-1 font-medium">Рег. номер</th>
                <th class="border border-neutral-800 px-2 py-1 font-medium">Название образца</th>
                <th class="border border-neutral-800 px-2 py-1 font-medium">Дата результата</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!samples.length">
                <td colspan="3" class="border border-neutral-800 px-2 py-3 text-center text-neutral-500">
                  Образцы не найдены.
                </td>
              </tr>
              <tr v-for="(sample, index) in samples" :key="sample.id">
                <td class="border border-neutral-800 px-2 py-1 text-center">{{ registrationNumber(sample, index) }}</td>
                <td class="border border-neutral-800 px-2 py-1">{{ sample.name ?? sample.title ?? "—" }}</td>
                <td class="border border-neutral-800 px-2 py-1 text-center italic">{{ formatShortDate(sample.completed_at) }}</td>
              </tr>
            </tbody>
          </table>

          <p v-for="note in sampleNotes" :key="note.regNumber" class="mb-1 text-[12px]">
            <span class="italic">Примечание к №{{ note.regNumber }}:</span>
            {{ note.comment }}
          </p>

          <p class="mt-4 mb-4 text-[13px]">
            <span class="font-bold">ЗАКЛЮЧЕНИЕ:</span>
            <USkeleton v-if="conclusionLoading" class="ml-2 inline-block h-4 w-64 align-middle" />
            <template v-else> {{ conclusionParagraph }}</template>
          </p>

          <div class="flex items-end justify-between text-[13px]">
            <span>Ответственный за выпуск:</span>
            <span class="min-w-40 border-b border-dashed border-neutral-500 text-right">&nbsp;</span>
          </div>
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex w-full justify-end">
        <UButton
          label="Закрыть"
          color="neutral"
          variant="ghost"
          @click="close"
        />
      </div>
    </template>
  </UModal>
</template>
