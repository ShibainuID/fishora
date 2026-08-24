import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TickMeter } from './tick-meter'

describe('TickMeter', () => {
  it('has no progressbar role and no filled track', () => {
    const { container } = render(<TickMeter value={0.91} />)
    expect(container.querySelector('[role="progressbar"]')).toBeNull()
    expect(container.querySelector('[class*="bg-"][class*="rounded-full"]')).toBeNull()
  })

  it('renders five hairline segments', () => {
    const { container } = render(<TickMeter value={0.91} />)
    expect(container.querySelectorAll('[data-tick]')).toHaveLength(5)
  })
})
