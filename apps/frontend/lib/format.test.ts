import { describe, expect, it } from 'vitest'
import {
  confidenceBand, countdown, kilograms, kilometres,
  normaliseDashes, percent, rupiah, rupiahPerKg,
} from './format'

describe('currency', () => {
  it('groups thousands the Indonesian way and welds Rp to the figure', () => {
    expect(rupiah(68000)).toBe('Rp 68.000')
  })
  it('keeps the per-kg suffix unbreakable', () => {
    expect(rupiahPerKg(68000)).toBe('Rp 68.000⁠/kg')
  })
  it('rounds rather than emitting fractional rupiah', () => {
    expect(rupiah(68000.6)).toBe('Rp 68.001')
  })
})

describe('units', () => {
  it('formats kilograms', () => expect(kilograms(24)).toBe('24 kg'))
  it('rounds distance, which is only a proxy', () =>
    expect(kilometres(37.4)).toBe('37 km'))
})

describe('confidence', () => {
  it('renders a percentage', () => expect(percent(0.91)).toBe('91%'))
  it.each([
    [0.91, 'high'], [0.85, 'high'], [0.7, 'medium'],
    [0.6, 'medium'], [0.48, 'low'],
  ])('bands %s as %s', (v, band) => expect(confidenceBand(v)).toBe(band))
})

describe('countdown', () => {
  it('uses h/m above an hour', () => expect(countdown(8_040_000)).toBe('2h 14m'))
  it('uses m:ss below an hour', () => expect(countdown(125_000)).toBe('2:05'))
  it('floors at zero rather than going negative', () =>
    expect(countdown(-5000)).toBe('0:00'))
})

describe('dash ban', () => {
  it('normalises em and en dashes from generated copy', () => {
    expect(normaliseDashes('firm — mild – white')).toBe('firm - mild - white')
  })
})
