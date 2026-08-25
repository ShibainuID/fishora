import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OperatorLots } from './operator-lots'
import { lotFixture } from '@/test/msw/fixtures'

vi.mock('@/lib/api/commerce', () => ({ allocateLot: vi.fn(), closeLot: vi.fn() }))
import { allocateLot, closeLot } from '@/lib/api/commerce'

describe('OperatorLots', () => {
  it('does not allocate on a single tap and names the buyer in a confirmation sheet', async () => {
    const user = userEvent.setup()
    render(<OperatorLots lots={[lotFixture({ status: 'closed' })]} />)
    await user.click(screen.getByRole('button', { name: 'Allocate to winning bidder' }))
    expect(allocateLot).not.toHaveBeenCalled()
    expect(screen.getByText(/Dewi Anggraini/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Konfirmasi' }))
    expect(allocateLot).toHaveBeenCalled()
  })

  it('closes an open auction from a confirmation sheet, not a single tap', async () => {
    const user = userEvent.setup()
    render(<OperatorLots lots={[lotFixture({ status: 'active' })]} />)
    await user.click(screen.getByRole('button', { name: 'Tutup lelang' }))
    expect(closeLot).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Konfirmasi tutup' }))
    expect(closeLot).toHaveBeenCalled()
  })

  it('offers the QR at every status, beside the status action', async () => {
    const user = userEvent.setup()
    render(<OperatorLots lots={[lotFixture({ status: 'active' })]} />)

    // The QR points at the public page for the lot, which an operator has
    // reason to show a buyer while the auction is still running. It used to
    // appear only once the lot was allocated.
    const qr = screen.getByRole('button', { name: 'Buat QR' })
    const close = screen.getByRole('button', { name: 'Tutup lelang' })
    expect(qr.parentElement).toBe(close.parentElement)

    await user.click(qr)
    expect(screen.getByRole('dialog', { name: /QR/i })).toBeInTheDocument()
  })

  it('names the species and status in words, not raw identifiers', () => {
    render(<OperatorLots lots={[lotFixture({ status: 'active' })]} />)
    expect(screen.getByText('Tenggiri')).toBeInTheDocument()
    expect(screen.queryByText('species_tenggiri')).not.toBeInTheDocument()
    expect(screen.getByText(/Berlangsung/)).toBeInTheDocument()
  })
})
