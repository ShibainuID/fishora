import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CARD, REASONS, lotFixture } from '@/test/msw/fixtures'
import { LotDetail } from './lot-detail'
import { ApiError } from '@/lib/api/errors'

vi.mock('@/lib/api/commerce', () => ({
  placeBid: vi.fn(),
  submitReview: vi.fn(),
  listReviews: vi.fn(),
}))

import { placeBid, submitReview, type Review } from '@/lib/api/commerce'

// mock: one buyer's experience of this species, shaped like the API response
const reviews: Review[] = [
  {
    id: 'rev_1',
    lot_id: 'lot_tenggiri_1',
    species_id: 'species_tenggiri',
    buyer_id: 'buyer_dewi',
    actual_use: 'Digoreng utuh untuk katering',
    processing_suitability: 4,
    substitute_acceptance: true,
    comment: 'Cocok untuk porsi rumah makan.',
    created_at: '2026-08-24T12:00:00+00:00',
  },
]

describe('LotDetail', () => {
  it('puts MatchReasons above the photograph and the bid in a phone bottom bar', () => {
    const { container } = render(
      <LotDetail
        lot={lotFixture()}
        card={CARD}
        reasons={REASONS}
        reviews={reviews}
        photoUrl="/fish/tenggiri.jpg"
      />
    )
    const reasons = screen.getByText(/cocok untuk digoreng/i)
    const photo = container.querySelector('img')
    expect(reasons.compareDocumentPosition(photo!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    const bar = screen.getByRole('button', { name: 'Ajukan penawaran' }).closest('div')
    expect(bar?.className).toContain('fixed')
    expect(bar?.className).toContain('lg:hidden')
  })

  it('blocks a bid at or below the highest before submit', async () => {
    const user = userEvent.setup()
    render(
      <LotDetail
        lot={lotFixture()}
        card={CARD}
        reasons={REASONS}
        reviews={reviews}
        photoUrl="/fish.jpg"
      />
    )
    await user.click(screen.getByRole('button', { name: 'Ajukan penawaran' }))
    const input = screen.getByLabelText('Harga per kg')
    await user.clear(input)
    await user.type(input, '70000')
    await user.click(screen.getByRole('button', { name: 'Kirim' }))
    expect(placeBid).not.toHaveBeenCalled()
    expect(screen.getByText(/harus di atas harga tertinggi/i)).toBeInTheDocument()
  })

  it('recovers from a 409 by prefilling the new minimum', async () => {
    const user = userEvent.setup()
    vi.mocked(placeBid).mockRejectedValueOnce(
      new ApiError('outbid', 409, undefined, '72000.00')
    )
    render(
      <LotDetail
        lot={lotFixture()}
        card={CARD}
        reasons={REASONS}
        reviews={reviews}
        photoUrl="/fish.jpg"
      />
    )
    await user.click(screen.getByRole('button', { name: 'Ajukan penawaran' }))
    await user.click(screen.getByRole('button', { name: 'Kirim' }))
    expect(await screen.findByDisplayValue('73000')).toBeInTheDocument()
    expect(screen.getByLabelText('Harga per kg')).not.toBeDisabled()
    expect(screen.getByText(/Harga tertinggi sekarang/)).toBeInTheDocument()
  })

  it('replaces the bid input with the outcome when closed', () => {
    render(
      <LotDetail
        lot={lotFixture({ status: 'closed' })}
        card={CARD}
        reasons={REASONS}
        reviews={reviews}
        photoUrl="/fish.jpg"
      />
    )
    expect(screen.getByText(/lelang selesai/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ajukan penawaran' })).toBeNull()
  })

  it('keeps KnowledgeCard and MarketSignals in separate containers', () => {
    render(
      <LotDetail
        lot={lotFixture()}
        card={CARD}
        reasons={[]}
        reviews={reviews}
        photoUrl="/fish.jpg"
      />
    )
    const knowledge = screen.getByText('Pengetahuan terverifikasi').closest('article')
    const signalsNode = screen.getByText('Sinyal pasar')
    const ancestors = (el: Element | null) => {
      const list: Element[] = []
      while (el) {
        list.push(el)
        el = el.parentElement
      }
      return list
    }
    const shared = ancestors(knowledge).filter((node) => ancestors(signalsNode).includes(node))
    expect(shared[0]).toHaveAttribute('data-page', 'lot-detail')
  })

  it('renders the real reviews the page fetched, not a hardcoded signal', () => {
    render(
      <LotDetail
        lot={lotFixture()}
        card={CARD}
        reasons={[]}
        reviews={reviews}
        photoUrl="/fish.jpg"
      />
    )
    expect(screen.getByText('Digoreng utuh untuk katering')).toBeInTheDocument()
    expect(screen.getByText('Cocok untuk porsi rumah makan.')).toBeInTheDocument()
    expect(screen.queryByText('Rumah Makan Cendana')).not.toBeInTheDocument()
  })

  it('shows an empty state, not a blank area, when no one has reviewed yet', () => {
    render(
      <LotDetail
        lot={lotFixture()}
        card={CARD}
        reasons={[]}
        reviews={[]}
        photoUrl="/fish.jpg"
      />
    )
    expect(screen.getByText(/belum ada umpan balik/i)).toBeInTheDocument()
  })

  it('hides the review form from anyone who is not the allocated buyer', () => {
    render(
      <LotDetail
        lot={lotFixture()}
        card={CARD}
        reasons={[]}
        reviews={reviews}
        photoUrl="/fish.jpg"
      />
    )
    expect(screen.queryByRole('button', { name: 'Kirim ulasan' })).toBeNull()
  })

  it('offers the review form to the allocated buyer and grows the list on submit', async () => {
    const user = userEvent.setup()
    vi.mocked(submitReview).mockResolvedValue({
      ...reviews[0],
      id: 'rev_2',
      actual_use: 'Dipepes',
      processing_suitability: 5,
      comment: null,
    })
    render(
      <LotDetail
        lot={lotFixture({ status: 'allocated', allocated_buyer_id: 'buyer_dewi' })}
        card={CARD}
        reasons={[]}
        reviews={reviews}
        canReview
        photoUrl="/fish.jpg"
      />
    )
    await user.type(screen.getByLabelText(/dipakai untuk apa/i), 'Dipepes')
    await user.click(screen.getByRole('button', { name: 'Kirim ulasan' }))
    expect(await screen.findByText('Dipepes')).toBeInTheDocument()
  })
})
