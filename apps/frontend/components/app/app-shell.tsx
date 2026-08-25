'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Fish, SquaresFour, Star, User, Sliders } from '@phosphor-icons/react/dist/ssr'
import { ThemeToggle } from '@/components/common/theme-toggle'
import { Z } from '@/lib/z'

const OPERATOR_TABS = [
  { href: '/operator', label: 'Identify', icon: Fish },
  { href: '/operator/lots', label: 'My lots', icon: SquaresFour },
  { href: '/account', label: 'Account', icon: User },
]

const BUYER_TABS = [
  { href: '/marketplace', label: 'Marketplace', icon: SquaresFour },
  { href: '/marketplace?matched=1', label: 'Matched', icon: Star },
  { href: '/preferences', label: 'Preferences', icon: Sliders },
  { href: '/account', label: 'Account', icon: User },
]

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const operator = pathname.startsWith('/operator')
  const tabs = operator ? OPERATOR_TABS : BUYER_TABS
  const role = operator ? 'Operator' : 'Buyer'

  return (
    <>
      <header
        className="sticky top-0 flex h-14 items-center justify-between border-b border-line bg-surface px-4 pt-[env(safe-area-inset-top)]"
        style={{ zIndex: Z.nav }}
      >
        {/* The wordmark is the way back to the marketing site. As plain text it
            left the two halves of the product with no link between them. */}
        {/* min-h-11: it is a tap target now, not a label. */}
        <Link href="/" className="text-h3 flex min-h-11 items-center text-ink">
          Fishora
        </Link>

        {/* The tab bar below is phone-only, so without this the app has no
            navigation at all above 1024px. */}
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary">
          {tabs.map((tab) => {
            const active = pathname === tab.href.split('?')[0]
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-current={active ? 'page' : undefined}
                className={[
                  'text-body-sm flex min-h-11 items-center rounded-full px-3',
                  active ? 'text-ink' : 'text-ink-muted hover:text-ink',
                ].join(' ')}
              >
                {tab.label}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-3">
          <p className="text-body-sm text-ink-muted">{role}</p>
          <ThemeToggle />
        </div>
      </header>
      {children}
      <nav
        className="fixed inset-x-0 bottom-0 flex border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] lg:hidden"
        style={{ zIndex: Z.nav }}
        aria-label="Primary, phone"
      >
        {tabs.map((tab) => {
          const Icon = tab.icon
          const active = pathname === tab.href.split('?')[0]
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={[
                'flex min-h-14 flex-1 flex-col items-center justify-center gap-1 text-body-sm',
                active ? 'text-ink' : 'text-ink-muted',
              ].join(' ')}
            >
              <Icon size={20} aria-hidden />
              {tab.label}
            </Link>
          )
        })}
      </nav>
    </>
  )
}
