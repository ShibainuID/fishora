import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FilterSheet } from './filter-sheet'
import { EMPTY_FILTERS } from '@/lib/marketplace-filters'

describe('FilterSheet', () => {
  it('opens species and price groups on arrival', () => {
    render(
      <FilterSheet
        open
        onClose={vi.fn()}
        filters={EMPTY_FILTERS}
        onChange={vi.fn()}
        resultCount={3}
      />
    )
    const species = screen.getByText('Spesies').closest('details')
    const price = screen.getByText('Harga').closest('details')
    const volume = screen.getByText('Volume').closest('details')
    expect(species).toHaveAttribute('open')
    expect(price).toHaveAttribute('open')
    expect(volume).not.toHaveAttribute('open')
  })
})
