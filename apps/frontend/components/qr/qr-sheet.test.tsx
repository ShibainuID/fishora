import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { QrSheet } from './qr-sheet'
import { discoverUrl } from '@/lib/qr'

function open() {
  return render(
    <QrSheet open onClose={vi.fn()} slug="kembung-01" speciesName="Kembung" />
  )
}

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('QrSheet', () => {
  it('carries a fish code and a Fishora code that say what each one opens', () => {
    open()
    const fish = screen.getByTestId('qr-code-fish')
    const app = screen.getByTestId('qr-code-app')
    expect(fish).toBeInTheDocument()
    expect(app).toBeInTheDocument()
    expect(fish).not.toBe(app)
    // Each block names its own destination, so a printed card is not ambiguous.
    expect(fish).toHaveTextContent(/Kembung/)
    expect(app).toHaveTextContent(/Fishora/)
    expect(screen.getByRole('img', { name: /Kembung/ })).toBeInTheDocument()
  })

  it('points the Fishora link at the site root by default', () => {
    open()
    expect(screen.getByRole('link', { name: 'Buka Fishora' })).toHaveAttribute('href', '/')
  })

  it('points the Fishora link at the configured app URL', () => {
    vi.stubEnv('NEXT_PUBLIC_APP_URL', 'https://fishora.example/app')
    open()
    expect(screen.getByRole('link', { name: 'Buka Fishora' })).toHaveAttribute(
      'href',
      'https://fishora.example/app'
    )
  })

  it('keeps the discover URL copyable', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    open()
    const url = discoverUrl('kembung-01')
    expect(screen.getByLabelText(/URL/)).toHaveValue(url)
    await user.click(screen.getByRole('button', { name: 'Salin URL' }))
    expect(writeText).toHaveBeenCalledWith(url)
    expect(screen.getByRole('button', { name: 'Disalin' })).toBeInTheDocument()
  })

  it('prints a real scannable code for Fishora, not just a URL to retype', () => {
    open()
    const app = screen.getByTestId('qr-code-app')
    // A shopper scans a card. A printed link they must retype is not the feature.
    const code = app.querySelector('img')
    expect(code).not.toBeNull()
    expect(code!.getAttribute('src')).toBe('/api/qr/app')
    expect(code!.getAttribute('alt')).toMatch(/fishora/i)
  })

  it('keeps the two codes distinguishable', () => {
    open()
    const fish = screen.getByTestId('qr-code-fish').querySelector('img')
    const app = screen.getByTestId('qr-code-app').querySelector('img')
    expect(fish!.getAttribute('src')).not.toBe(app!.getAttribute('src'))
  })
})
