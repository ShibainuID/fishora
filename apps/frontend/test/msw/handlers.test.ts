import { describe, expect, it } from 'vitest'
import { ALL_SPECIES_IDS, BUYERS, LOTS, PEOPLE } from './fixtures'
import { handlers } from './handlers'

describe('MSW fixtures', () => {
  it('covers the 11 supported species and locked demo names', () => {
    expect(ALL_SPECIES_IDS).toHaveLength(11)
    expect(ALL_SPECIES_IDS.every((id) => id.startsWith('species_'))).toBe(true)
    expect(LOTS.every((lot) => ALL_SPECIES_IDS.includes(lot.species_id))).toBe(true)
    expect(BUYERS.pasar).toBe('Pasar Segar Nusantara')
    expect(BUYERS.cendana).toBe('Rumah Makan Cendana')
    expect(BUYERS.prima).toBe('Sentra Boga Prima')
    expect(PEOPLE.operator).toBe('Rian Setiawan')
    expect(PEOPLE.buyer).toBe('Dewi Anggraini')
  })

  it('registers handlers for the live schema paths', () => {
    const info = handlers.map((handler) => handler.info.header)
    expect(info.some((row) => row.includes('/api/v1/lots'))).toBe(true)
    expect(info.some((row) => row.includes('/api/v1/buyers'))).toBe(true)
    expect(info.some((row) => row.includes('/api/v1/discover'))).toBe(true)
    expect(info.some((row) => row.includes('/api/v1/auth/login'))).toBe(true)
    expect(info.some((row) => row.includes('/api/v1/auth/me'))).toBe(true)
    expect(info.some((row) => row.includes('/api/v1/auth/logout'))).toBe(true)
    expect(info.some((row) => row.includes('/close'))).toBe(true)
  })
})
