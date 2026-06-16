import { inject, type Ref } from 'vue'

interface ToastApi {
  notify: (message: string) => void
  notifySuccess: (message: string) => void
  notifyWarning: (message: string) => void
  notifyError: (message: string) => void
  dismiss: (id: number) => void
}

const TOAST_KEY = Symbol('toast')

export function useToast(): ToastApi {
  const api = inject<ToastApi>(TOAST_KEY)
  if (!api) {
    const noop = () => {}
    return { notify: noop, notifySuccess: noop, notifyWarning: noop, notifyError: noop, dismiss: noop }
  }
  return api
}

export { TOAST_KEY }
