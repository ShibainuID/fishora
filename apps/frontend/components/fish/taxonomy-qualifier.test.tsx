import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TaxonomyQualifier } from './taxonomy-qualifier'

describe('TaxonomyQualifier', () => {
  it('renders nothing for VERIFIED_TAXONOMY', () => {
    const { container } = render(
      <TaxonomyQualifier status="VERIFIED_TAXONOMY" label="bandeng" />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders a visible qualifier for TAXONOMY_REVIEW_REQUIRED', () => {
    render(<TaxonomyQualifier status="TAXONOMY_REVIEW_REQUIRED" label="gembolo" />)
    expect(screen.getByText(/tinjauan/i)).toBeInTheDocument()
  })

  it('pairs an icon with words so the qualifier is never icon-only', () => {
    const { container } = render(
      <TaxonomyQualifier status="TAXONOMY_REVIEW_REQUIRED" label="gembolo" />
    )
    expect(container.querySelector('svg')).toBeTruthy()
    expect(screen.getByText(/tinjauan/i)).toBeInTheDocument()
  })

  it('explains genus-level locking for MIXED_TAXONOMY on tuna', () => {
    render(<TaxonomyQualifier status="MIXED_TAXONOMY" label="tuna" />)
    expect(screen.getByText(/genus/i)).toBeInTheDocument()
    expect(screen.getByText(/Thunnus/i)).toBeInTheDocument()
  })
})
