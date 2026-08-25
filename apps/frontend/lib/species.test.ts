import { describe, expect, it } from 'vitest'
import { resolveSpecies, SUPPORTED_LABELS } from './species'

describe('resolveSpecies', () => {
  it('resolves every supported label to an Indonesian name and a photograph', () => {
    // The list is the species we hold catch photography for, so a supported
    // label without a real photo is the failure this guards against.
    expect(SUPPORTED_LABELS.length).toBeGreaterThan(0)
    for (const label of SUPPORTED_LABELS) {
      const resolved = resolveSpecies(label)
      expect(resolved.commonName).toBeTruthy()
      expect(resolved.commonName).not.toBe(label)
      expect(resolved.photo).not.toBe('/sea.jpg')
      expect(resolved.photo).toMatch(/^\/[\w-]+\.(jpe?g|png|webp)$/)
    }
  })

  it('returns the raw label for an unknown model output rather than throwing', () => {
    expect(resolveSpecies('ikan_baru_2027')).toEqual({
      commonName: 'ikan_baru_2027',
      scientificName: null,
      // Open water, never another species' photograph.
      photo: '/sea.jpg',
    })
  })

  it('locks tenggiri to Scomberomorus commerson and tuna to Thunnus spp.', () => {
    expect(resolveSpecies('tenggiri').scientificName).toBe('Scomberomorus commerson')
    expect(resolveSpecies('tuna').scientificName).toBe('Thunnus spp.')
    expect(resolveSpecies('gembolo').scientificName).toBeNull()
  })
})
