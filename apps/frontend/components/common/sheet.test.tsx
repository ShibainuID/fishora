import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Sheet } from './sheet'

function sheet(open: boolean) {
  return render(
    <Sheet open={open} onClose={vi.fn()} title="Filter">
      <p>Isi panel</p>
    </Sheet>
  )
}

describe('Sheet', () => {
  it('stays out of the way when closed', () => {
    sheet(false)
    const dialog = document.querySelector('dialog')!
    // A bare `flex` on the dialog overrides the browser rule that hides a
    // closed dialog, which leaves the panel permanently on screen over the
    // page. Display must be driven by the [open] attribute.
    expect(dialog.className).toContain('hidden')
    expect(dialog.className).toContain('open:flex')
    expect(dialog.className).not.toMatch(/(^|\s)flex(\s|$)/)
    expect(dialog.open).toBe(false)
  })

  it('opens as a modal in the top layer', () => {
    sheet(true)
    expect(document.querySelector('dialog')!.open).toBe(true)
    expect(screen.getByText('Isi panel')).toBeInTheDocument()
  })

  it('locks the page behind it while open', () => {
    sheet(true)
    expect(document.body.style.overflow).toBe('hidden')
  })

  it('releases the scroll lock when it closes', () => {
    const { unmount } = sheet(true)
    unmount()
    expect(document.body.style.overflow).not.toBe('hidden')
  })

  it('names itself for assistive tech', () => {
    sheet(true)
    expect(document.querySelector('dialog')!.getAttribute('aria-label')).toBe('Filter')
  })
})
