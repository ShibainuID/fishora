import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MarketplaceView } from './marketplace-view'
import { LOTS } from '@/test/msw/fixtures'

vi.mock('next/image', () => ({
  default: ({ alt, src }: { alt: string; src: string }) => <img alt={alt} src={src} />,
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => '/marketplace',
  useSearchParams: () => new URLSearchParams('species=tenggiri'),
}))

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

describe('MarketplaceView', () => {
  it('shows a phone Filters button with an active count, not a rail', () => {
    render(<MarketplaceView lots={LOTS} inventoryEmpty={false} />)
    expect(screen.getByRole('button', { name: /filters 1/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /filters 1/i }).className).toContain('lg:hidden')
  })

  it('keeps active pills on one scrolling row and distinguishes empty states', () => {
    const { rerender, container } = render(
      <MarketplaceView lots={LOTS} inventoryEmpty={false} />
    )
    const pills = container.querySelector('.overflow-x-auto')
    expect(pills?.className).toContain('whitespace-nowrap')
    expect(pills?.className).not.toContain('flex-wrap')

    rerender(<MarketplaceView lots={[]} inventoryEmpty />)
    expect(screen.getByText('Belum ada lot aktif.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Muat ulang' })).toBeInTheDocument()

    rerender(<MarketplaceView lots={[]} inventoryEmpty={false} />)
    expect(screen.getByText('Tidak ada lot yang cocok dengan filter ini.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hapus filter' })).toBeInTheDocument()
  })

  it('shows the score the matching engine returned, not a placeholder', () => {
    vi.doMock('next/navigation', () => ({
      useRouter: () => ({ replace: vi.fn() }),
      usePathname: () => '/marketplace',
      useSearchParams: () => new URLSearchParams('matched=1'),
    }))
    render(
      <MarketplaceView
        lots={LOTS}
        inventoryEmpty={false}
        matched
        matchScores={{ [LOTS[0].id]: 0.94 }}
      />
    )
    // A hardcoded 90% would make every lot look equally good, which defeats
    // the point of explainable matching.
    expect(screen.getByText(/94% cocok/)).toBeInTheDocument()
    expect(screen.queryByText(/90% cocok/)).not.toBeInTheDocument()
  })

  it('prompts for a profile when the matching engine reports none', () => {
    render(
      <MarketplaceView
        lots={[]}
        inventoryEmpty={false}
        matched
        matchScores={{}}
        profileMissing
      />
    )
    expect(screen.getByText(/buat profil preferensi/i)).toBeInTheDocument()
  })

  it('does not show match scores outside the matched view', () => {
    render(<MarketplaceView lots={LOTS} inventoryEmpty={false} matchScores={{ [LOTS[0].id]: 0.94 }} />)
    expect(screen.queryByText(/94% cocok/)).not.toBeInTheDocument()
  })
})
