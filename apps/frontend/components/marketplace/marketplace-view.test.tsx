import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MarketplaceView } from './marketplace-view'
import { listLots } from '@/lib/api/commerce'
import { LOTS, lotFixture } from '@/test/msw/fixtures'

vi.mock('@/lib/api/commerce', () => ({
  listLots: vi.fn(),
}))

// jsdom always reports a visible tab, so the poll's own gate needs a lever.
let hidden = false
Object.defineProperty(document, 'visibilityState', {
  configurable: true,
  get: () => (hidden ? 'hidden' : 'visible'),
})

vi.mock('next/image', () => ({
  // eslint-disable-next-line @next/next/no-img-element -- stubbing next/image is the point
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

describe('MarketplaceView live updates', () => {
  const NEW_LOT = lotFixture({
    id: 'lot_tenggiri_baru',
    public_slug: 'tenggiri-baru',
    quantity_kg: '31.000',
  })

  beforeEach(() => {
    vi.useFakeTimers()
    vi.mocked(listLots).mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  const tick = async (ms: number) => {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ms)
    })
  }

  it('renders a lot that arrived after the first paint', async () => {
    vi.mocked(listLots).mockResolvedValue([...LOTS, NEW_LOT])
    const { container } = render(<MarketplaceView lots={LOTS} inventoryEmpty={false} />)
    expect(container.querySelector('a[href="/marketplace/lot_tenggiri_baru"]')).toBeNull()

    await tick(15_000)

    expect(container.querySelector('a[href="/marketplace/lot_tenggiri_baru"]')).not.toBeNull()
  })

  it('polls with the filters in the url, not an empty query', async () => {
    vi.mocked(listLots).mockResolvedValue(LOTS)
    render(<MarketplaceView lots={LOTS} inventoryEmpty={false} />)

    await tick(15_000)

    expect(listLots).toHaveBeenCalledWith('species_id=species_tenggiri&status=active')
    expect(listLots).not.toHaveBeenCalledWith('')
  })

  it('does not poll in the matched view', async () => {
    vi.mocked(listLots).mockResolvedValue([...LOTS, NEW_LOT])
    render(<MarketplaceView lots={LOTS} inventoryEmpty={false} matched />)

    await tick(60_000)

    expect(listLots).not.toHaveBeenCalled()
  })

  it('keeps the last good list when a poll fails', async () => {
    vi.mocked(listLots).mockRejectedValue(new Error('offline'))
    const { container } = render(<MarketplaceView lots={LOTS} inventoryEmpty={false} />)

    await tick(30_000)

    expect(container.querySelector('a[href="/marketplace/lot_tenggiri_1"]')).not.toBeNull()
    expect(screen.queryByText('Tidak ada lot yang cocok dengan filter ini.')).toBeNull()
  })

  it('counts new arrivals instead of reordering silently', async () => {
    vi.mocked(listLots).mockResolvedValue([...LOTS, NEW_LOT])
    render(<MarketplaceView lots={LOTS} inventoryEmpty={false} />)

    await tick(15_000)

    const badge = screen.getByRole('button', { name: /1 lot baru/i })
    expect(badge).toBeInTheDocument()
    expect(badge.className).toContain('min-h-11')
  })

  it('stops polling while the tab is hidden and resumes when it returns', async () => {
    vi.mocked(listLots).mockResolvedValue(LOTS)
    render(<MarketplaceView lots={LOTS} inventoryEmpty={false} />)

    await tick(15_000)
    expect(listLots).toHaveBeenCalledTimes(1)

    hidden = true
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await tick(60_000)
    expect(listLots).toHaveBeenCalledTimes(1)

    hidden = false
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
    })
    expect(listLots).toHaveBeenCalledTimes(2)
  })
})
