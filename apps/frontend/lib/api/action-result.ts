import type { ApiErrorKind } from './errors'

export type ActionFailure = {
  ok: false
  kind: ApiErrorKind
  userMessage: string
  retryable: boolean
  status: number
}

export type ActionResult<T> = { ok: true; data: T } | ActionFailure
