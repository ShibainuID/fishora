import { describe, expect, it } from 'vitest'
import { activeFilterCount, parseFilters, serializeFilters } from './marketplace-filters'

describe('marketplace filters', () => {
  it('round-trips through the URL query', () => {
    const query = 'species=tenggiri,kembung&min_price=50000&max_price=90000&matched=1'
    const filters = parseFilters(query)
    expect(filters.species).toEqual(['tenggiri', 'kembung'])
    expect(filters.minPrice).toBe('50000')
    expect(filters.matched).toBe(true)
    expect(parseFilters(serializeFilters(filters))).toEqual(filters)
    expect(activeFilterCount(filters)).toBe(2)
  })
})
