import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch } from './client'

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

afterEach(() => vi.unstubAllGlobals())

describe('apiFetch error mapping', () => {
  it.each([
    [503, 'cv_unavailable', true],
    [409, 'not_verified', false],
    [404, 'not_found', false],
    [422, 'unsupported_species', false],
    [502, 'generation_unavailable', true],
    [413, 'image_too_large', false],
  ])('maps %s to %s (retryable=%s)', async (status, kind, retryable) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(status, { detail: 'x' })))
    const err = await apiFetch('/api/v1/fish/identify').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.kind).toBe(kind)
    expect(err.retryable).toBe(retryable)
  })

  it('keeps retrieved_chunk_ids so a generation failure is diagnosable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      jsonResponse(502, { detail: 'nope', retrieved_chunk_ids: ['c1', 'c2'] })
    ))
    const err = await apiFetch('/x').catch((e) => e)
    expect(err.retrievedChunkIds).toEqual(['c1', 'c2'])
  })

  it('maps a network failure to offline, not to a server error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const err = await apiFetch('/x').catch((e) => e)
    expect(err.kind).toBe('offline')
    expect(err.retryable).toBe(true)
  })

  it('never leaks the raw detail string into the user message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      jsonResponse(503, { detail: 'http://internal-cv:8001 refused' })
    ))
    const err = await apiFetch('/x').catch((e) => e)
    expect(err.userMessage).not.toContain('internal-cv')
  })

  it('returns parsed JSON on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, { ok: 1 })))
    await expect(apiFetch<{ ok: number }>('/x')).resolves.toEqual({ ok: 1 })
  })
})
