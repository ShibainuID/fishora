import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MarketSignals } from './market-signals'

const signals = [
  {
    businessType: 'Restoran',
    useCase: 'Digoreng',
    body: 'Dagingnya padat, cocok untuk porsi besar.',
  },
  {
    businessType: 'Pengolah',
    useCase: 'Fillet',
    body: 'Hasil fillet rapi, sedikit tulang.',
  },
]

describe('MarketSignals', () => {
  it('renders its own heading and the not-verified-knowledge note', () => {
    render(<MarketSignals signals={signals} />)
    expect(
      screen.getByRole('heading', { name: 'Sinyal pasar' })
    ).toBeInTheDocument()
    expect(
      screen.getByText('Umpan balik pembeli dan konsumen. Bukan pengetahuan terverifikasi.')
    ).toBeInTheDocument()
  })

  it('does not render the verified shield mark or the verified left edge', () => {
    const { container } = render(<MarketSignals signals={signals} />)
    expect(screen.queryByText('Pengetahuan terverifikasi')).not.toBeInTheDocument()
    const root = container.firstElementChild
    expect(root?.className).not.toMatch(/border-l-2|border-l-\[2px\]/)
    expect(root?.className).not.toMatch(/border-l-verified/)
  })

  it('renders an empty state rather than an empty box when the list is empty', () => {
    const { container } = render(<MarketSignals signals={[]} />)
    expect(screen.getByText(/belum ada umpan balik/i)).toBeInTheDocument()
    expect(container.querySelectorAll('article, li')).toHaveLength(0)
  })

  it('shows each reviewer business type and stated use case', () => {
    render(<MarketSignals signals={signals} />)
    expect(screen.getByText('Restoran')).toBeInTheDocument()
    expect(screen.getByText('Digoreng')).toBeInTheDocument()
    expect(screen.getByText('Pengolah')).toBeInTheDocument()
    expect(screen.getByText('Fillet')).toBeInTheDocument()
  })
})
