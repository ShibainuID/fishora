import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Select } from './select'

const OPTIONS = [
  { value: 'a', label: 'Rumah makan' },
  { value: 'b', label: 'Katering' },
]

describe('Select', () => {
  it('ties the label to the control', () => {
    render(<Select label="Jenis usaha" options={OPTIONS} defaultValue="a" />)
    const select = screen.getByLabelText('Jenis usaha')
    expect(select.tagName).toBe('SELECT')
  })

  it('paints the option list instead of leaving it to the browser', () => {
    render(<Select label="Jenis usaha" options={OPTIONS} defaultValue="a" />)
    // A transparent select inherits near-white text from the dark theme while
    // Chrome still paints the popup on white, so the choices come out white on
    // white. The popup is rendered outside the page, so utility classes never
    // reach it and the colours have to be inline on each option.
    for (const option of screen.getAllByRole('option')) {
      expect(option).toHaveStyle({ backgroundColor: 'var(--color-bg)' })
      expect(option).toHaveStyle({ color: 'var(--color-ink)' })
    }
  })

  it('gives the control an opaque background of its own', () => {
    render(<Select label="Jenis usaha" options={OPTIONS} defaultValue="a" />)
    const select = screen.getByLabelText('Jenis usaha')
    expect(select.className).toContain('bg-surface')
    expect(select.className).not.toContain('bg-transparent')
  })

  it('keeps a 44px target', () => {
    render(<Select label="Jenis usaha" options={OPTIONS} defaultValue="a" />)
    expect(screen.getByLabelText('Jenis usaha').className).toContain('min-h-11')
  })

  it('describes itself with helper text', () => {
    render(<Select label="Jenis usaha" helper="Segmen pembeli." options={OPTIONS} />)
    const select = screen.getByLabelText('Jenis usaha')
    expect(select).toHaveAccessibleDescription('Segmen pembeli.')
  })

  it('reports an error over the helper', () => {
    render(
      <Select label="Jenis usaha" helper="Segmen pembeli." error="Wajib diisi." options={OPTIONS} />
    )
    expect(screen.getByLabelText('Jenis usaha')).toHaveAccessibleDescription('Wajib diisi.')
    expect(screen.getByLabelText('Jenis usaha')).toHaveAttribute('aria-invalid', 'true')
  })
})
