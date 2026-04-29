import { computed, ref } from 'vue'
import type { ResearchSample, ResearchStatus, User } from '@/shared/types'

const patients: User[] = [
  { id: 101, name: 'Анна Смирнова', email: 'anna.smirnova@example.com', location: 'Москва', status: 'subscribed', avatar: { src: 'https://i.pravatar.cc/128?img=47' } },
  { id: 102, name: 'Игорь Волков', email: 'igor.volkov@example.com', location: 'Казань', status: 'subscribed', avatar: { src: 'https://i.pravatar.cc/128?img=12' } },
  { id: 103, name: 'Мария Орлова', email: 'maria.orlova@example.com', location: 'Санкт-Петербург', status: 'bounced', avatar: { src: 'https://i.pravatar.cc/128?img=32' } },
  { id: 104, name: 'Павел Соколов', email: 'pavel.sokolov@example.com', location: 'Екатеринбург', status: 'unsubscribed', avatar: { src: 'https://i.pravatar.cc/128?img=68' } },
  { id: 105, name: 'Елена Кузнецова', email: 'elena.kuznetsova@example.com', location: 'Новосибирск', status: 'subscribed', avatar: { src: 'https://i.pravatar.cc/128?img=5' } }
]

const statuses: ResearchStatus[] = ['registered', 'inProgress', 'review', 'completed', 'rejected']
const materials = ['Кровь', 'Сыворотка', 'Плазма', 'Мазок', 'Моча']
const directions = ['Биохимия', 'Гематология', 'ПЦР', 'Иммунология', 'Микробиология']
const actors = ['Регистратор', 'Лаборант', 'Врач КДЛ', 'Контроль качества']

function addHours(date: Date, hours: number) {
  return new Date(date.getTime() + hours * 60 * 60 * 1000)
}

function makeHistory(index: number, currentStatus: ResearchStatus, baseDate: Date) {
  const currentIndex = statuses.indexOf(currentStatus)
  const path = currentStatus === 'rejected'
    ? ['registered', 'inProgress', 'rejected'] as ResearchStatus[]
    : statuses.slice(0, currentIndex + 1).filter(status => status !== 'rejected')

  return path.map((status, step) => ({
    id: index * 10 + step,
    status,
    date: addHours(baseDate, step * 7).toISOString(),
    actor: actors[step % actors.length],
    note: status === 'registered'
      ? 'Образец принят и промаркирован.'
      : status === 'completed'
        ? 'Исследование завершено, результаты доступны.'
        : status === 'rejected'
          ? 'Образец отклонён после первичной проверки.'
          : 'Статус обновлён по лабораторному процессу.'
  }))
}

function makeResearchSample(index: number): ResearchSample {
  const patient = patients[index % patients.length]
  const status = statuses[index % statuses.length]
  const registeredAt = addHours(new Date('2026-04-12T08:30:00.000Z'), index * 9)
  const updatedAt = addHours(registeredAt, statuses.indexOf(status) * 7 + 2)

  return {
    id: index + 1,
    code: `BIO-${String(2600 + index).padStart(5, '0')}`,
    patient,
    material: materials[index % materials.length],
    direction: directions[index % directions.length],
    priority: index % 6 === 0 ? 'urgent' : 'normal',
    status,
    registeredAt: registeredAt.toISOString(),
    updatedAt: updatedAt.toISOString(),
    comment: index % 4 === 0 ? 'Требуется контроль срока доставки образца.' : 'Плановая лабораторная обработка.',
    tests: [
      {
        id: index * 100 + 1,
        code: 'CRP',
        group: 'Воспаление',
        name: 'C-реактивный белок',
        method: 'Иммунотурбидиметрия',
        applies: true,
        result: index % 3 === 0 ? '12.4' : '4.8',
        reference: '0-5',
        unit: 'мг/л',
        note: index % 3 === 0 ? 'Повышение требует контроля.' : '',
        interpretation: index % 3 === 0 ? 'warning' : 'normal'
      },
      {
        id: index * 100 + 2,
        code: 'WBC',
        group: 'Гематология',
        name: 'Лейкоциты',
        method: 'Гематологический анализатор',
        applies: true,
        result: index % 2 === 0 ? '8.1' : '5.6',
        reference: '4.0-9.0',
        unit: '10^9/л',
        note: '',
        interpretation: 'normal'
      },
      {
        id: index * 100 + 3,
        code: 'GLU',
        group: 'Биохимия',
        name: 'Глюкоза',
        method: 'Гексокиназный',
        applies: true,
        result: index % 5 === 0 ? '6.3' : '5.1',
        reference: '3.9-5.8',
        unit: 'ммоль/л',
        note: index % 5 === 0 ? 'Выше референса.' : '',
        interpretation: index % 5 === 0 ? 'warning' : 'normal'
      },
      {
        id: index * 100 + 4,
        code: 'ALT',
        group: 'Биохимия',
        name: 'АЛТ',
        method: 'IFCC',
        applies: index % 7 !== 0,
        result: index % 7 === 0 ? 'ожидается' : '28',
        reference: '0-41',
        unit: 'Ед/л',
        note: index % 7 === 0 ? 'Результат в работе.' : '',
        interpretation: index % 7 === 0 ? 'pending' : 'normal'
      }
    ],
    history: makeHistory(index, status, registeredAt)
  }
}

const allSamples: ResearchSample[] = Array.from({ length: 72 }, (_, index) => makeResearchSample(index))

export function useResearchSamples() {
  const samples = ref<ResearchSample[]>(allSamples)
  const isFetching = ref(false)

  const statusCounts = computed(() => samples.value.reduce<Record<ResearchStatus, number>>((acc, sample) => {
    acc[sample.status] += 1
    return acc
  }, {
    registered: 0,
    inProgress: 0,
    review: 0,
    completed: 0,
    rejected: 0
  }))

  return {
    samples,
    isFetching,
    statusCounts
  }
}
