'use client'

import { useLayoutEffect } from 'react'
import { Moon, Sun } from '@phosphor-icons/react/dist/ssr'
import { applyTheme, readTheme, resolvedTheme } from '@/lib/theme'

/**
 * ThemeToggle. DESIGN.md 3.1.
 *
 * Deliberately holds no React state. The current theme already lives in one
 * place, the `data-theme` attribute that the inline script set during HTML
 * parsing, so both icons render and CSS picks. That keeps the button correct
 * during SSR, on hydration, and after an external theme change, with no
 * mismatch and no cascading render. The accessible name is toggled by the same
 * rule, since an aria-label cannot be driven by CSS.
 *
 * The useLayoutEffect is a repair, not the mechanism: React Strict Mode
 * remounts once in development and resets <html> to the attributes it manages
 * from JSX, wiping what the inline script set. No-op in production.
 */
export function ThemeToggle() {
  useLayoutEffect(() => {
    const stored = readTheme()
    if (stored !== 'system') applyTheme(stored)
  }, [])

  return (
    <button
      type="button"
      onClick={() => applyTheme(resolvedTheme() === 'dark' ? 'light' : 'dark')}
      className="grid size-11 shrink-0 place-items-center rounded-full text-ink-muted transition-colors hover:bg-bg-sunken hover:text-ink active:scale-[0.98]"
    >
      <Moon className="size-5 dark:hidden" aria-hidden />
      <Sun className="hidden size-5 dark:block" aria-hidden />
      <span className="sr-only dark:hidden">Switch to dark theme</span>
      <span className="sr-only hidden dark:block">Switch to light theme</span>
    </button>
  )
}
