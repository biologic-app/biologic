type TourAction = () => void | Promise<void>

const actions = new Map<string, TourAction>()

// Позволяет странице зарегистрировать именованное действие (например «открыть
// мастер создания» или «открыть карточку по первой строке»), которое шаг тура
// запускает перед тем, как ждать появления своей цели — см. AppTourStep.action.
export function registerTourAction(key: string, action: TourAction) {
  actions.set(key, action)
  return () => {
    if (actions.get(key) === action) {
      actions.delete(key)
    }
  }
}

export async function runTourAction(key: string | undefined) {
  if (!key) {
    return
  }

  await actions.get(key)?.()
}
