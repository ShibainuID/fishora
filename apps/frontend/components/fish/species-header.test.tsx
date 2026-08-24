import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SpeciesHeader } from '@/components/fish/species-header'
import { SUPPORTED_LABELS } from '@/lib/species'

describe('SpeciesHeader', () => {
  it('resolves every supported label to a visible Indonesian name', () => {
    const { rerender } = render(<SpeciesHeader label="bandeng" />)
    for (const label of SUPPORTED_LABELS) {
      rerender(<SpeciesHeader label={label} />)
      expect(screen.getByRole('heading')).not.toHaveTextContent(label)
    }
  })

  it('renders an unknown label as-is so a model update cannot white-screen', () => {
    render(<SpeciesHeader label="ikan_baru_2027" />)
    expect(screen.getByRole('heading')).toHaveTextContent('ikan_baru_2027')
  })

  it('renders the scientific name in italic', () => {
    render(<SpeciesHeader label="tenggiri" />)
    const sci = screen.getByText('Scomberomorus commerson')
    expect(sci.tagName).toBe('P')
    expect(sci.className).toMatch(/italic/)
  })

  it('pairs the verified mark with the word Terverifikasi, not an icon alone', () => {
    render(<SpeciesHeader label="bandeng" verified />)
    expect(screen.getByText('Terverifikasi')).toBeInTheDocument()
  })
})
