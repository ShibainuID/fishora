'use client'

import { useLayoutEffect } from 'react'
import { Moon, Sun } from '@phosphor-icons/react/dist/ssr'
import { applyTheme, readTheme, resolvedTheme } from '@/lib/theme'

// Holds no state: `data-theme` is the source of truth, both icons render and
// CSS picks. Avoids an SSR/hydration mismatch.
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
