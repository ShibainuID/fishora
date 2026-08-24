import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CARD, REASONS, lotFixture } from '@/test/msw/fixtures'
import { LotDetail } from './lot-detail'
import { ApiError } from '@/lib/api/errors'

vi.mock('@/lib/api/commerce', () => ({
  placeBid: vi.fn(),
}))

import { placeBid } from '@/lib/api/commerce'

const signals = [{ businessType: 'Rumah Makan Cendana', useCase: 'Digoreng' }] // mock

describe('LotDetail', () => {
  it('puts MatchReasons above the photograph and the bid in a phone bottom bar', () => {
    const { container } = render(
      <LotDetail
        lot={lotFixture()}
        card={CARD}
        reasons={REASONS}
        signals={signals}
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
        signals={signals}
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
        signals={signals}
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
        signals={signals}
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
        signals={signals}
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
})
