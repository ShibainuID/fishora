import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SpeciesArt } from './species-art'

describe('SpeciesArt', () => {
  it('names the species it stands in for', () => {
    render(<SpeciesArt label="tenggiri" />)
    expect(screen.getByRole('img', { name: 'Ilustrasi Tenggiri' })).toBeInTheDocument()
    expect(screen.getByText('Tenggiri')).toBeInTheDocument()
  })

  it('falls back to the raw label for a species it does not know', () => {
    render(<SpeciesArt label="ikan_baru" />)
    expect(screen.getByRole('img', { name: 'Ilustrasi ikan_baru' })).toBeInTheDocument()
  })

  it('leaves positioning to the caller', () => {
    // The root must not set its own position: a position utility here beats the
    // caller's by stylesheet order, so `absolute inset-0` goes inert and the
    // box collapses to zero height with every child absolutely positioned.
    render(<SpeciesArt label="tuna" className="absolute inset-0" />)
    const root = screen.getByRole('img', { name: 'Ilustrasi Tuna' })
    expect(root.className).toContain('absolute inset-0')
    expect(root.className).not.toMatch(/(^|\s)relative(\s|$)/)
  })

  it('gives the strata a positioned box of their own', () => {
    render(<SpeciesArt label="tuna" className="absolute inset-0" />)
    const inner = screen.getByRole('img', { name: 'Ilustrasi Tuna' }).firstElementChild!
    expect(inner.className).toContain('relative')
    expect(inner.className).toContain('size-full')
  })

  it('is stable for a given species and different across species', () => {
    const { container: a } = render(<SpeciesArt label="tuna" />)
    const { container: b } = render(<SpeciesArt label="tuna" />)
    const { container: c } = render(<SpeciesArt label="kembung" />)
    expect(a.innerHTML).toBe(b.innerHTML)
    expect(a.innerHTML).not.toBe(c.innerHTML)
  })
})
