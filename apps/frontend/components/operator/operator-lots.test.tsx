import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OperatorLots } from './operator-lots'
import { lotFixture } from '@/test/msw/fixtures'

vi.mock('@/lib/api/commerce', () => ({ allocateLot: vi.fn() }))
import { allocateLot } from '@/lib/api/commerce'

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
})
