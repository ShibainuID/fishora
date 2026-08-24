import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api/errors'
import { ReviewForm } from './review-form'

vi.mock('@/lib/api/commerce', () => ({
  submitReview: vi.fn(),
  listReviews: vi.fn(),
}))

import { submitReview, type Review } from '@/lib/api/commerce'

beforeEach(() => {
  vi.mocked(submitReview).mockReset()
})

function created(overrides: Partial<Review> = {}): Review {
  return {
    id: 'rev_1',
    lot_id: 'lot_tenggiri_1',
    species_id: 'species_tenggiri',
    buyer_id: 'buyer_dewi',
    actual_use: 'Digoreng utuh',
    processing_suitability: 4,
    substitute_acceptance: true,
    comment: 'Dagingnya padat.',
    created_at: '2026-08-24T12:00:00+00:00',
    ...overrides,
  }
}

describe('ReviewForm', () => {
  it('sends the typed values exactly once on an explicit submit', async () => {
    const user = userEvent.setup()
    vi.mocked(submitReview).mockResolvedValue(created())
    render(<ReviewForm lotId="lot_tenggiri_1" />)

    await user.type(screen.getByLabelText(/dipakai untuk apa/i), 'Digoreng utuh')
    await user.click(screen.getByRole('radio', { name: '4' }))
    await user.click(screen.getByRole('checkbox', { name: /pengganti/i }))
    await user.type(screen.getByLabelText(/catatan/i), 'Dagingnya padat.')
    expect(submitReview).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Kirim ulasan' }))
    await waitFor(() => expect(submitReview).toHaveBeenCalledTimes(1))
    expect(vi.mocked(submitReview).mock.calls[0]).toEqual([
      'lot_tenggiri_1',
      {
        actual_use: 'Digoreng utuh',
        processing_suitability: 4,
        substitute_acceptance: true,
        comment: 'Dagingnya padat.',
      },
    ])
  })

  it('never autosaves: typing and picking a rating send nothing', async () => {
    const user = userEvent.setup()
    vi.mocked(submitReview).mockResolvedValue(created())
    render(<ReviewForm lotId="lot_tenggiri_1" />)

    await user.type(screen.getByLabelText(/dipakai untuk apa/i), 'Dibakar')
    await user.click(screen.getByRole('radio', { name: '2' }))
    expect(submitReview).not.toHaveBeenCalled()
  })

  it('omits an empty comment rather than sending a blank string', async () => {
    const user = userEvent.setup()
    vi.mocked(submitReview).mockResolvedValue(created({ comment: null }))
    render(<ReviewForm lotId="lot_tenggiri_1" />)

    await user.type(screen.getByLabelText(/dipakai untuk apa/i), 'Dibakar')
    await user.click(screen.getByRole('button', { name: 'Kirim ulasan' }))
    await waitFor(() => expect(submitReview).toHaveBeenCalledTimes(1))
    expect(vi.mocked(submitReview).mock.calls[0][1]).not.toHaveProperty('comment')
  })

  it('blocks a submit with no stated use instead of sending an invalid body', async () => {
    const user = userEvent.setup()
    render(<ReviewForm lotId="lot_tenggiri_1" />)

    await user.click(screen.getByRole('button', { name: 'Kirim ulasan' }))
    expect(submitReview).not.toHaveBeenCalled()
    expect(screen.getByText(/tulis dulu/i)).toBeInTheDocument()
  })

  it('renders a readable message on 403, not a status code', async () => {
    const user = userEvent.setup()
    vi.mocked(submitReview).mockRejectedValue(new ApiError('server', 403))
    render(<ReviewForm lotId="lot_tenggiri_1" />)

    await user.type(screen.getByLabelText(/dipakai untuk apa/i), 'Digoreng utuh')
    await user.click(screen.getByRole('button', { name: 'Kirim ulasan' }))

    const message = await screen.findByText(/hanya bisa ditulis oleh pembeli/i)
    expect(message).toBeInTheDocument()
    expect(screen.queryByText(/403/)).not.toBeInTheDocument()
  })

  it('renders a readable message on 409, not a status code', async () => {
    const user = userEvent.setup()
    vi.mocked(submitReview).mockRejectedValue(new ApiError('not_verified', 409))
    render(<ReviewForm lotId="lot_tenggiri_1" />)

    await user.type(screen.getByLabelText(/dipakai untuk apa/i), 'Digoreng utuh')
    await user.click(screen.getByRole('button', { name: 'Kirim ulasan' }))

    const message = await screen.findByText(/belum dialokasikan/i)
    expect(message).toBeInTheDocument()
    expect(screen.queryByText(/409/)).not.toBeInTheDocument()
  })

  it('renders a readable message on 401 rather than failing silently', async () => {
    const user = userEvent.setup()
    vi.mocked(submitReview).mockRejectedValue(new ApiError('server', 401))
    render(<ReviewForm lotId="lot_tenggiri_1" />)

    await user.type(screen.getByLabelText(/dipakai untuk apa/i), 'Digoreng utuh')
    await user.click(screen.getByRole('button', { name: 'Kirim ulasan' }))

    expect(await screen.findByText(/masuk sebagai pembeli/i)).toBeInTheDocument()
  })

  it('offers the rating as five discrete options, never as a filled track', () => {
    const { container } = render(<ReviewForm lotId="lot_tenggiri_1" />)
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(container.querySelectorAll('progress, [style*="width"]')).toHaveLength(0)
    expect(container.querySelectorAll('input[type="range"]')).toHaveLength(0)
    const options = screen.getAllByRole('radio')
    expect(options).toHaveLength(5)
    expect(options.map((option) => option.getAttribute('value'))).toEqual([
      '1', '2', '3', '4', '5',
    ])
  })

  it('keeps every rating option at a 44px tap target', () => {
    render(<ReviewForm lotId="lot_tenggiri_1" />)
    for (const option of screen.getAllByRole('radio')) {
      const target = option.closest('label')
      expect(target?.className).toContain('min-h-11')
      expect(target?.className).toContain('min-w-11')
    }
  })

  it('reports the saved review to its parent so the list can grow', async () => {
    const user = userEvent.setup()
    const review = created()
    vi.mocked(submitReview).mockResolvedValue(review)
    const onSubmitted = vi.fn()
    render(<ReviewForm lotId="lot_tenggiri_1" onSubmitted={onSubmitted} />)

    await user.type(screen.getByLabelText(/dipakai untuk apa/i), 'Digoreng utuh')
    await user.click(screen.getByRole('button', { name: 'Kirim ulasan' }))
    await waitFor(() => expect(onSubmitted).toHaveBeenCalledWith(review))
  })
})
