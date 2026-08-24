'use client'

import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { X } from '@phosphor-icons/react/dist/ssr'
import { Z } from '@/lib/z'

/** Must match the `duration-300` class on the panel. */
const SLIDE_MS = 300

export interface SheetProps {
  open: boolean
  onClose: () => void
  title: string
  footer?: ReactNode
  children: ReactNode
}

export function Sheet({ open, onClose, title, footer, children }: SheetProps) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const node = ref.current
    if (open && node && !node.open) node.showModal()
  }, [open])

  // Backstop: if transitionend never fires the dialog would stay open and keep
  // the focus trap forever.
  useEffect(() => {
    if (open) return
    const node = ref.current
    if (!node?.open) return
    const timer = setTimeout(() => node.close(), SLIDE_MS + 60)
    return () => clearTimeout(timer)
  }, [open])

  // Escape fires `cancel`; route it through onClose so parent state stays authoritative.
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

  // Scroll lock: without it the page behind scrolls under the thumb on iOS.
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
        if (event.target === ref.current) onClose()
      }}
      className={[
        'fixed inset-0 m-0 h-full max-h-none w-full max-w-none bg-transparent p-0',
        'flex items-end justify-center md:items-center',
        'backdrop:bg-abyss-950/55',
      ].join(' ')}
    >
      <div
        // Inline, not a data-variant utility: both states write `translate`, so
        // this avoids depending on utility ordering.
        style={{ translate: open ? '0 0' : '0 100%' }}
        onClick={(event) => event.stopPropagation()}
        onTransitionEnd={(event) => {
          if (event.target !== event.currentTarget) return
          // Tailwind v4 animates the `translate` property, not `transform`.
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
