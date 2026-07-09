import type { StepperItem } from "@nuxt/ui";

export interface TimelineStepperEvent {
  id: string | number;
  label: string;
  description: string;
  actor?: string | null;
  date?: string | null;
}

export function timelineEventsToStepperItems(
  events: TimelineStepperEvent[],
  icon = "i-lucide-circle-dot",
): StepperItem[] {
  return events.map((event) => ({
    value: String(event.id),
    title: event.label,
    description: event.description,
    icon,
    actor: event.actor ?? null,
    date: event.date ?? null,
  }));
}

export function getLastStepperIndex(items: readonly unknown[]) {
  return Math.max(items.length - 1, 0);
}

export const timelineStepperUi = {
  header: "gap-4",
  item: "items-start",
  trigger: "shrink-0",
  wrapper: "mt-0 min-w-0 pb-1",
  title: "text-sm font-semibold text-highlighted",
  description: "whitespace-pre-line break-words text-xs leading-5 text-muted",
  separator: "min-h-8",
} as const;
