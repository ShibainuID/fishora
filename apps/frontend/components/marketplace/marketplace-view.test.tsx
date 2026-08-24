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
})
