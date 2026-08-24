'use client'

import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { X } from '@phosphor-icons/react/dist/ssr'
import { Z } from '@/lib/z'

/**
 * Sheet. DESIGN.md 8.10.
 *
 * Bottom sheet on phones, centred dialog at md. On phones this is the primary
 * surface for filters, bidding and the nav menu, so it gets a real focus trap,
 * real Escape handling and a real scroll lock rather than a div with a shadow.
 *
 * Three deliberate choices:
 *
 * 1. Built on <dialog>, so the top layer, the focus trap and inert background
 *    content come from the browser instead of from our own key handlers.
 * 2. The element is a transparent full-viewport container and the panel is
 *    positioned inside it. Relying on the dialog's own margin centring to
 *    produce a bottom sheet is fragile across browsers.
 * 3. The slide is a CSS transition on a permanently mounted panel, not a
 *    JS-driven presence animation. close() removes the element from the top
 *    layer, so it must not run until the slide has finished, and `transitionend`
 *    is the one signal that is exactly that. It also means no animation library
 *    on the critical path, and whatever the user typed into a filter sheet
 *    survives dismissing it by accident.
 *
 * Reduced motion needs no branch here: the global backstop in globals.css
 * collapses the duration, and `transitionend` still fires.
 */

/** Must stay in step with the `duration-300` class on the panel below. */
const SLIDE_MS = 300

export interface SheetProps {
  open: boolean
  onClose: () => void
  title: string
  /** Pinned to the bottom edge of the panel, above the safe area. */
  footer?: ReactNode
  children: ReactNode
}

export function Sheet({ open, onClose, title, footer, children }: SheetProps) {
  const ref = useRef<HTMLDialogElement>(null)

  // Open immediately. Closing waits for the slide to finish, below.
  useEffect(() => {
    const node = ref.current
    if (open && node && !node.open) node.showModal()
  }, [open])

  // Backstop. `transitionend` does the closing, but if it never arrives (an
  // interrupted transition, a display change mid-slide, a browser quirk) an
  // open <dialog> would keep the focus trap and the inert background forever.
  // A stuck modal is a far worse failure than a slide that ends abruptly.
  useEffect(() => {
    if (open) return
    const node = ref.current
    if (!node?.open) return
    const timer = setTimeout(() => node.close(), SLIDE_MS + 60)
    return () => clearTimeout(timer)
  }, [open])

  // Escape fires `cancel`. Route it through onClose so the parent's state stays
  // the single source of truth rather than the DOM.
  useEffect(() => {
    const node = ref.current
    if (!node) return
    const onCancel = (event: Event) => {
      event.preventDefault()
      onClose()
    }
    node.addEventListener('cancel', onCancel)
    return () => node.removeEventListener('cancel', onCancel)
  }, [onClose])

  // Scroll lock. Without it the page behind scrolls under the thumb on iOS,
  // which is the most common bottom-sheet defect there is.
  useEffect(() => {
    if (!open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [open])

  return (
    <dialog
      ref={ref}
      style={{ zIndex: Z.modal }}
      aria-label={title}
      onClick={(event) => {
        // The panel stops propagation, so reaching here means the press landed
        // on the backdrop.
        if (event.target === ref.current) onClose()
      }}
      className={[
        'fixed inset-0 m-0 h-full max-h-none w-full max-w-none bg-transparent p-0',
        'flex items-end justify-center md:items-center',
        'backdrop:bg-abyss-950/55',
      ].join(' ')}
    >
      <div
        // Set inline rather than through a data-variant utility: both states
        // write the same `translate` property, and an inline value settles which
        // one wins without depending on utility ordering or specificity.
        style={{ translate: open ? '0 0' : '0 100%' }}
        onClick={(event) => event.stopPropagation()}
        onTransitionEnd={(event) => {
          // Only the panel's own movement, not a child's transition bubbling up.
          if (event.target !== event.currentTarget) return
          // Tailwind v4's translate-y-* utilities animate the `translate`
          // property, not `transform`, so the event names `translate` here.
          // Both are accepted so this survives either implementation.
          if (!['translate', 'transform'].includes(event.propertyName)) return
          if (!open) ref.current?.close()
        }}
        className={[
          'flex w-full flex-col bg-surface',
          'max-h-[88dvh] md:max-h-[85dvh] md:w-[min(34rem,calc(100vw-3rem))]',
          'rounded-t-[var(--radius-card)] md:rounded-[var(--radius-card)]',
          'shadow-[var(--shadow-e3)]',
          'transition-transform duration-300 ease-[var(--ease-out-quint)]',
        ].join(' ')}
      >
        <header className="flex items-center justify-between gap-4 border-b border-line px-4 py-3">
          <h2 className="text-h3 text-ink">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="grid size-11 shrink-0 place-items-center rounded-full text-ink-muted transition-colors hover:bg-bg-sunken hover:text-ink active:scale-[0.98]"
          >
            <X className="size-5" aria-hidden />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4">
          {children}
        </div>

        {footer && (
          <footer className="border-t border-line px-4 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
            {footer}
          </footer>
        )}
      </div>
    </dialog>
  )
}
