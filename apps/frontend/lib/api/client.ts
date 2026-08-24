import { ApiError, kindFromResponse } from './errors'

export { ApiError }
export type { ApiErrorKind } from './errors'

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
const DEFAULT_TIMEOUT_MS = 35_000 // above the backend's 30s CV timeout

export interface ApiFetchOptions extends RequestInit {
  timeoutMs?: number
}

export async function apiFetch<T>(
  path: string,
  { timeoutMs = DEFAULT_TIMEOUT_MS, ...init }: ApiFetchOptions = {}
): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, { ...init, signal: controller.signal })
  } catch (cause) {
    // An aborted request is a timeout; anything else at this layer is the
    // network being gone. Neither is a server error, and conflating them
    // produces the wrong UI: a Retry button for a problem retrying cannot fix.
    const aborted = cause instanceof DOMException && cause.name === 'AbortError'
    throw new ApiError(aborted ? 'timeout' : 'offline', 0)
  } finally {
    clearTimeout(timer)
  }

  if (!response.ok) {
    let detail = ''
    let chunkIds: string[] | undefined
    try {
      const body = await response.json()
      detail = typeof body?.detail === 'string' ? body.detail : ''
      chunkIds = Array.isArray(body?.retrieved_chunk_ids) ? body.retrieved_chunk_ids : undefined
    } catch {
      // A non-JSON error body is still an error; the status carries enough.
    }
    throw new ApiError(kindFromResponse(response.status, detail), response.status, chunkIds)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
