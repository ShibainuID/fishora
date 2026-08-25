import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FlowStrip } from './flow-strip'

describe('FlowStrip', () => {
  it('advances on its own without a scrollbar', () => {
    const { container } = render(<FlowStrip />)
    const strip = container.querySelector('#flow')!
    // The strip is driven by a transform on the track, not by the scroll
    // position, so the container must not be a scroll container.
    expect(strip.className).toContain('overflow-hidden')
    expect(strip.className).not.toContain('overflow-x-auto')
    expect(container.querySelector('.marquee-track')).not.toBeNull()
  })

  it('names all eight steps once for assistive tech', () => {
    render(<FlowStrip />)
    // The track is duplicated so the loop has somewhere to go; the copy is
    // hidden, so the eight steps must still be announced exactly once each.
    expect(screen.getByRole('heading', { name: 'Catch' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Fishora QR' })).toBeInTheDocument()
    expect(screen.getAllByRole('heading')).toHaveLength(8)
  })

  it('renders the duplicate pass so the loop has no seam', () => {
    const { container } = render(<FlowStrip />)
    expect(container.querySelectorAll('article')).toHaveLength(16)
    expect(container.querySelectorAll('article[aria-hidden="true"]')).toHaveLength(8)
  })

  it('gives every step its own sentence', () => {
    const { container } = render(<FlowStrip />)
    const lines = [...container.querySelectorAll('article[aria-hidden="true"] h3 + p')].map(
      (p) => p.textContent
    )
    // Every panel used to carry one identical sentence, which told a reader
    // nothing about the step it sat under.
    expect(new Set(lines).size).toBe(8)
  })

  it('pauses while a reader is on it', () => {
    const { container } = render(<FlowStrip />)
    const track = container.querySelector('.marquee-track')!
    expect(track.className).toContain('group-hover:[animation-play-state:paused]')
    expect(track.className).toContain('group-focus-within:[animation-play-state:paused]')
  })
})
