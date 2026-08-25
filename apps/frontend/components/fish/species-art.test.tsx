import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SpeciesArt } from './species-art'
import { SUPPORTED_LABELS, SPECIES } from '@/lib/species'

describe('SpeciesArt', () => {
  it('shows the catch photograph for a species we hold one for', () => {
    render(<SpeciesArt label="tenggiri" />)
    expect(screen.getByRole('img', { name: 'Foto Tenggiri' })).toBeInTheDocument()
    expect(screen.getByText('Tenggiri')).toBeInTheDocument()
  })

  it('gives every supported species its own photograph', () => {
    const photos = SUPPORTED_LABELS.map((label) => SPECIES[label].photo)
    // A duplicate would put one species' fish on another species' card.
    expect(new Set(photos).size).toBe(photos.length)
  })

  it('falls back to open water for a species it does not know', () => {
    render(<SpeciesArt label="ikan_baru" />)
    // Never another species' fish: an unrecognised label with a confident-looking
    // photograph of the wrong fish is worse than no photograph.
    expect(screen.getByRole('img', { name: 'Ilustrasi ikan_baru' })).toBeInTheDocument()
  })

  it('leaves positioning to the caller', () => {
    // The root must not set its own position: a position utility here beats the
    // caller's by stylesheet order, so `absolute inset-0` goes inert and the
    // box collapses to zero height with every child absolutely positioned.
    render(<SpeciesArt label="tuna" className="absolute inset-0" />)
    const root = screen.getByRole('img', { name: 'Foto Tuna' })
    expect(root.className).toContain('absolute inset-0')
    expect(root.className).not.toMatch(/(^|\s)relative(\s|$)/)
  })

  it('gives the image a positioned box of its own', () => {
    render(<SpeciesArt label="tuna" className="absolute inset-0" />)
    const inner = screen.getByRole('img', { name: 'Foto Tuna' }).firstElementChild!
    expect(inner.className).toContain('relative')
    expect(inner.className).toContain('size-full')
  })
})
