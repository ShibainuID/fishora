import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { lotFixture } from '@/test/msw/fixtures'
import { LotCard } from './lot-card'

vi.mock('next/image', () => ({
  default: ({ alt, src }: { alt: string; src: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img alt={alt} src={src} />
  ),
}))

const PHOTO = '/fish/tenggiri.jpg'

describe('LotCard', () => {
  it('keeps captions off the photograph and shows a live dot only while open', () => {
    const { container, rerender } = render(
      <LotCard lot={lotFixture()} photoUrl={PHOTO} />
    )
    const media = container.querySelector('.aspect-\\[4\\/3\\]')
    expect(media?.textContent?.trim()).toBe('')
    expect(screen.getByText('Berlangsung')).toBeInTheDocument()
    expect(screen.queryByText('Selesai')).toBeNull()
    expect(screen.queryByText(/cocok/)).toBeNull()

    rerender(<LotCard lot={lotFixture({ status: 'closed' })} photoUrl={PHOTO} />)
    expect(screen.getByText('Selesai')).toBeInTheDocument()
    expect(screen.queryByText('Berlangsung')).toBeNull()
  })

  it('shows the match percentage only in the matched view and lifts only at lg', () => {
    const { container } = render(
      <LotCard lot={lotFixture()} photoUrl={PHOTO} matchPercent={0.9} />
    )
    expect(screen.getByText('90% cocok')).toBeInTheDocument()
    expect(container.firstElementChild?.className).toContain('lg:hover:-translate-y-[2px]')
    expect(container.querySelector('[role="progressbar"]')).toBeNull()
  })
})
