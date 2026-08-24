import { describe, expect, it } from 'vitest'
import { resolveSpecies, SUPPORTED_LABELS } from './species'

describe('resolveSpecies', () => {
  it('resolves all 11 supported labels to an Indonesian name', () => {
    expect(SUPPORTED_LABELS).toHaveLength(11)
    for (const label of SUPPORTED_LABELS) {
      const resolved = resolveSpecies(label)
      expect(resolved.commonName).toBeTruthy()
      expect(resolved.commonName).not.toBe(label)
    }
  })

  it('returns the raw label for an unknown model output rather than throwing', () => {
    expect(resolveSpecies('ikan_baru_2027')).toEqual({
      commonName: 'ikan_baru_2027',
      scientificName: null,
    })
  })

  it('locks tenggiri to Scomberomorus commerson and tuna to Thunnus spp.', () => {
    expect(resolveSpecies('tenggiri').scientificName).toBe('Scomberomorus commerson')
    expect(resolveSpecies('tuna').scientificName).toBe('Thunnus spp.')
    expect(resolveSpecies('gembolo').scientificName).toBeNull()
  })
})
