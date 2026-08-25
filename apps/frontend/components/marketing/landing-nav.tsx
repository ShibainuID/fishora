'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { List, X } from '@phosphor-icons/react/dist/ssr'
import { Logo } from '@/components/common/logo'

const LINKS = [
  { href: '#platform', label: 'Platform' },
  { href: '#buyers', label: 'Buyers' },
  { href: '#operators', label: 'Operators' },
  { href: '#knowledge', label: 'Knowledge' },
]

const PRODUCT = [
  { href: '/marketplace', label: 'Marketplace' },
  { href: '/operator', label: 'Operator app' },
]

export function LandingNav() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = previous
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <header className="sticky top-0 z-40 bg-abyss-950/92 lg:backdrop-blur-xl">
      <div className="mx-auto flex h-[60px] w-full max-w-[1200px] items-center gap-3 px-4 lg:h-[68px] lg:px-8">
        <Link href="/" className="flex min-h-11 items-center text-[1.0625rem]">
          <Logo />
        </Link>

        <nav className="ml-auto hidden items-center gap-1 lg:flex" aria-label="Primary">
          {LINKS.map((link) => (
            <a key={link.href} className="flex min-h-11 items-center px-3" href={link.href}>
              {link.label}
            </a>
          ))}
          <span aria-hidden className="mx-2 h-5 w-px bg-abyss-800" />
          {PRODUCT.map((link) => (
            <Link key={link.href} className="flex min-h-11 items-center px-3" href={link.href}>
              {link.label}
            </Link>
          ))}
        </nav>

        {/* The CTA never hides behind the menu: it is the one action the page asks for. */}
        <Link
          href="/account"
          className="text-body-sm ml-auto inline-flex min-h-11 items-center justify-center rounded-full bg-accent px-5 font-medium text-accent-ink lg:ml-6"
        >
          Request access
        </Link>

        <button
          type="button"
          className="grid size-11 place-items-center lg:hidden"
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
          aria-controls="landing-menu"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <X size={22} /> : <List size={22} />}
        </button>
      </div>

      {/* Without this the trigger was decorative and phones had no navigation
          at all: the link row is hidden below lg. */}
      {open && (
        <div
          id="landing-menu"
          className="fixed inset-x-0 top-[60px] bottom-0 overflow-y-auto bg-abyss-950 px-4 pb-10 lg:hidden"
        >
          <nav aria-label="Primary, phone" className="flex flex-col">
            {LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="text-h3 flex min-h-14 items-center border-b border-abyss-900"
              >
                {link.label}
              </a>
            ))}
            {PRODUCT.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="text-h3 flex min-h-14 items-center border-b border-abyss-900 text-accent"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  )
}
