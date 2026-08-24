import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MarketSignals } from './market-signals'
import type { Review } from '@/lib/api/commerce'

function reviewFixture(overrides: Partial<Review> = {}): Review {
  return {
    id: 'rev_1',
    lot_id: 'lot_tenggiri_1',
    species_id: 'species_tenggiri',
    buyer_id: 'buyer_dewi',
    actual_use: 'Digoreng utuh',
    processing_suitability: 4,
    substitute_acceptance: true,
    comment: 'Dagingnya padat, cocok untuk porsi besar.',
    created_at: '2026-08-24T12:00:00+00:00',
    ...overrides,
  }
}

const reviews: Review[] = [
  reviewFixture(),
  reviewFixture({
    id: 'rev_2',
    actual_use: 'Fillet',
    processing_suitability: 5,
    substitute_acceptance: false,
    comment: 'Hasil fillet rapi, sedikit tulang.',
  }),
]

describe('MarketSignals', () => {
  it('renders its own heading and the not-verified-knowledge note', () => {
    render(<MarketSignals reviews={reviews} />)
    expect(
      screen.getByRole('heading', { name: 'Sinyal pasar' })
    ).toBeInTheDocument()
    expect(
      screen.getByText('Umpan balik pembeli dan konsumen. Bukan pengetahuan terverifikasi.')
    ).toBeInTheDocument()
  })

  it('does not render the verified shield mark or the verified left edge', () => {
    const { container } = render(<MarketSignals reviews={reviews} />)
    expect(screen.queryByText('Pengetahuan terverifikasi')).not.toBeInTheDocument()
    const root = container.firstElementChild
    expect(root?.className).not.toMatch(/border-l-2|border-l-\[2px\]/)
    expect(root?.className).not.toMatch(/border-l-verified/)
  })

  it('keeps the sunken ground the unverified surface is drawn on', () => {
    const { container } = render(<MarketSignals reviews={reviews} />)
    expect(container.firstElementChild?.className).toContain('bg-bg-sunken')
  })

  it('renders an empty state rather than an empty box when the list is empty', () => {
    const { container } = render(<MarketSignals reviews={[]} />)
    expect(screen.getByText(/belum ada umpan balik/i)).toBeInTheDocument()
    expect(container.querySelectorAll('article, li')).toHaveLength(0)
  })

  it('renders the stated use, suitability and comment of every real review', () => {
    render(<MarketSignals reviews={reviews} />)
    expect(screen.getByText('Digoreng utuh')).toBeInTheDocument()
    expect(screen.getByText('Fillet')).toBeInTheDocument()
    expect(screen.getByText(/4 dari 5/)).toBeInTheDocument()
    expect(screen.getByText(/5 dari 5/)).toBeInTheDocument()
    expect(screen.getByText('Dagingnya padat, cocok untuk porsi besar.')).toBeInTheDocument()
    expect(screen.getByText('Hasil fillet rapi, sedikit tulang.')).toBeInTheDocument()
  })

  it('states suitability as a discrete count, never as a filled progress track', () => {
    const { container } = render(<MarketSignals reviews={reviews} />)
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(container.querySelectorAll('progress, [style*="width"]')).toHaveLength(0)
  })

  it('still shows the note when there is nothing to show yet', () => {
    render(<MarketSignals reviews={[]} />)
    expect(
      screen.getByText('Umpan balik pembeli dan konsumen. Bukan pengetahuan terverifikasi.')
    ).toBeInTheDocument()
  })
})
