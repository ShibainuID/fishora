import { afterEach, describe, expect, it, vi } from 'vitest'
import { getKnowledge, identifyFish, verifySpecies } from './fish'

function ok(body: unknown) {
  return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } })
}
afterEach(() => vi.unstubAllGlobals())

describe('identifyFish', () => {
  it('sends the image under the field name the backend expects', async () => {
    const spy = vi.fn().mockResolvedValue(ok({ prediction_id: 'p1' }))
    vi.stubGlobal('fetch', spy)
    await identifyFish(new File(['x'], 'ikan.jpg', { type: 'image/jpeg' }))
    const body = spy.mock.calls[0][1].body as FormData
    expect(body.get('file')).toBeInstanceOf(File)
    expect(spy.mock.calls[0][0]).toContain('/api/v1/fish/identify')
  })
  it('does not set content-type, so the boundary is generated', async () => {
    const spy = vi.fn().mockResolvedValue(ok({}))
    vi.stubGlobal('fetch', spy)
    await identifyFish(new File(['x'], 'a.jpg', { type: 'image/jpeg' }))
    expect(spy.mock.calls[0][1].headers ?? {}).not.toHaveProperty('Content-Type')
  })
})

describe('verifySpecies', () => {
  it('posts snake_case keys', async () => {
    const spy = vi.fn().mockResolvedValue(ok({}))
    vi.stubGlobal('fetch', spy)
    await verifySpecies('p1', 'species_tenggiri')
    expect(JSON.parse(spy.mock.calls[0][1].body)).toEqual({
      prediction_id: 'p1', verified_species_id: 'species_tenggiri',
    })
  })
})

describe('getKnowledge', () => {
  it('is scoped to the prediction, never to a species', async () => {
    const spy = vi.fn().mockResolvedValue(ok({}))
    vi.stubGlobal('fetch', spy)
    await getKnowledge('p1')
    expect(spy.mock.calls[0][0]).toContain('/api/v1/predictions/p1/knowledge')
  })
})
