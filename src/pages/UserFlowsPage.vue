<script setup lang="ts">
import { ref } from "vue";
import type { TabsItem } from "@nuxt/ui";
import { useWorkflowRole } from "@/modules/workflows/useWorkflowRole";

const activeTab = ref<"flow" | "screens" | "rules">("flow");
const { selectedEntityActions, selectedRole, selectedScreens } = useWorkflowRole();

const tabs: TabsItem[] = [
  { label: "Поток", icon: "i-lucide-git-branch", slot: "flow" },
  { label: "Экраны", icon: "i-lucide-panels-top-left", slot: "screens" },
  { label: "Правила", icon: "i-lucide-shield-check", slot: "rules" },
];
</script>

<template>
  <UDashboardPanel id="user-flows">
    <template #header>
      <UDashboardNavbar title="Потоки ролей" :ui="{ right: 'gap-2' }">
        <template #leading>
          <UDashboardSidebarCollapse />
        </template>

        <template #right>
          <UBadge
            :label="selectedRole.entryPoint"
            color="neutral"
            variant="outline"
          />
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <div class="flex min-w-0 items-center gap-3">
            <UBadge
              :label="selectedRole.shortName"
              color="primary"
              variant="solid"
              class="shrink-0"
            />
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold text-highlighted">
                {{ selectedRole.title }}
              </p>
              <p class="truncate text-xs text-muted">
                {{ selectedRole.entryPoint }}
              </p>
            </div>
          </div>
        </template>

        <template #right>
          <UButton
            :to="selectedRole.route"
            icon="i-lucide-arrow-up-right"
            label="Открыть рабочий экран"
            color="neutral"
            variant="outline"
          />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <section class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <div class="rounded-lg border border-default bg-elevated/40 p-5">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <UBadge :label="selectedRole.shortName" color="primary" variant="subtle" />
                  <UBadge label="UX flow" color="neutral" variant="outline" />
                </div>
                <h1 class="mt-3 text-2xl font-semibold text-highlighted">
                  {{ selectedRole.title }}
                </h1>
                <p class="mt-2 max-w-3xl text-sm leading-6 text-muted">
                  {{ selectedRole.subtitle }}
                </p>
              </div>

              <div class="flex shrink-0 flex-wrap gap-2">
                <UButton
                  v-for="action in selectedRole.actions"
                  :key="action.label"
                  :to="action.route"
                  :icon="action.icon"
                  :label="action.label"
                  :color="action.primary ? 'primary' : 'neutral'"
                  :variant="action.primary ? 'solid' : 'outline'"
                />
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-default bg-elevated/40 p-5">
            <p class="text-xs font-medium uppercase text-muted">
              Основной вход
            </p>
            <p class="mt-2 text-xl font-semibold text-highlighted">
              {{ selectedRole.entryPoint }}
            </p>
            <p class="mt-2 text-sm text-muted">
              Рабочий сценарий начинается с очереди, а не с общей таблицы: пользователь сразу попадает к задачам, которые может выполнить.
            </p>
          </div>
        </section>

        <UPageGrid class="gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <UPageCard
            v-for="metric in selectedRole.metrics"
            :key="metric.label"
            :icon="metric.icon"
            :title="metric.label"
            variant="subtle"
            :ui="{
              container: 'gap-y-1.5',
              leading: 'rounded-md bg-elevated p-2 ring ring-default',
              title: 'text-xs font-normal uppercase text-muted',
            }"
          >
            <div class="flex items-center justify-between gap-3">
              <span class="text-2xl font-semibold text-highlighted">
                {{ metric.value }}
              </span>
              <UBadge :color="metric.tone" variant="subtle" label="queue" />
            </div>
          </UPageCard>
        </UPageGrid>

        <section class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
          <div class="rounded-lg border border-default">
            <div class="border-b border-default px-4 pt-4">
              <UTabs
                v-model="activeTab"
                :items="tabs"
                variant="link"
                :content="false"
              />
            </div>

            <div class="p-4">
              <div v-if="activeTab === 'flow'" class="space-y-4">
                <div
                  v-for="(step, index) in selectedRole.flow"
                  :key="step.title"
                  class="grid grid-cols-[2rem_minmax(0,1fr)] gap-3"
                >
                  <div class="flex flex-col items-center">
                    <div class="flex size-8 items-center justify-center rounded-full bg-primary text-sm font-semibold text-inverted">
                      {{ index + 1 }}
                    </div>
                    <div
                      v-if="index < selectedRole.flow.length - 1"
                      class="min-h-8 w-px flex-1 bg-border"
                    />
                  </div>

                  <div class="pb-4">
                    <div class="flex flex-wrap items-center gap-2">
                      <h3 class="text-sm font-semibold text-highlighted">
                        {{ step.title }}
                      </h3>
                      <UBadge
                        v-if="step.status"
                        :label="step.status"
                        color="neutral"
                        variant="outline"
                        size="xs"
                      />
                    </div>
                    <p class="mt-1 text-sm leading-6 text-muted">
                      {{ step.description }}
                    </p>
                  </div>
                </div>
              </div>

              <div v-else-if="activeTab === 'screens'" class="grid gap-3 md:grid-cols-2">
                <div
                  v-for="screen in selectedScreens"
                  :key="screen.id"
                  class="rounded-lg border border-default p-3"
                >
                  <div class="flex items-center gap-3">
                    <UIcon name="i-lucide-monitor" class="size-4 shrink-0 text-muted" />
                    <span class="text-sm font-medium text-highlighted">{{ screen.title }}</span>
                  </div>
                  <div class="mt-2 flex flex-wrap gap-2">
                    <UBadge
                      :label="screen.route"
                      color="neutral"
                      variant="outline"
                      size="xs"
                    />
                    <UBadge
                      :label="screen.mode"
                      color="primary"
                      variant="subtle"
                      size="xs"
                    />
                  </div>
                </div>
              </div>

              <div v-else class="space-y-3">
                <UAlert
                  v-for="rule in selectedRole.constraints"
                  :key="rule"
                  icon="i-lucide-shield-check"
                  color="neutral"
                  variant="subtle"
                  :description="rule"
                />
                <div class="rounded-lg border border-default p-4">
                  <p class="mb-3 text-sm font-semibold text-highlighted">
                    Доступные UI-действия
                  </p>
                  <div class="flex flex-wrap gap-2">
                    <UBadge
                      v-for="action in selectedEntityActions"
                      :key="`${action.resource}.${action.action}`"
                      :label="action.label"
                      color="neutral"
                      variant="subtle"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <aside class="space-y-3">
            <div
              v-for="queue in selectedRole.queues"
              :key="queue.title"
              class="rounded-lg border border-default bg-elevated/40 p-4"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="flex min-w-0 items-start gap-3">
                  <div class="rounded-md bg-default p-2 ring ring-default">
                    <UIcon :name="queue.icon" class="size-4 text-muted" />
                  </div>
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold text-highlighted">
                      {{ queue.title }}
                    </p>
                    <p class="mt-1 text-xs leading-5 text-muted">
                      {{ queue.description }}
                    </p>
                  </div>
                </div>
                <UBadge :color="queue.tone" :label="String(queue.count)" variant="subtle" />
              </div>

              <div class="mt-3 flex items-center justify-between gap-2">
                <UBadge :label="queue.status" color="neutral" variant="outline" />
                <UButton
                  :to="queue.route"
                  icon="i-lucide-arrow-up-right"
                  color="neutral"
                  variant="ghost"
                  size="sm"
                />
              </div>
            </div>
          </aside>
        </section>
      </div>
    </template>
  </UDashboardPanel>
</template>
