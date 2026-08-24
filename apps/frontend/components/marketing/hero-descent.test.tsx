import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { HeroDescent } from './hero-descent'

vi.mock('motion/react', async () => {
  const actual = await vi.importActual<typeof import('motion/react')>('motion/react')
  return {
    ...actual,
    useReducedMotion: () => true,
  }
})

describe('HeroDescent', () => {
  it('renders the static hero when motion is reduced and does not register scroll listeners', () => {
    const spy = vi.spyOn(window, 'addEventListener')
    const { container } = render(<HeroDescent />)
    expect(container.querySelector('[data-block="hero"]')).toBeTruthy()
    expect(container.querySelector('.h-\\[320vh\\]')).toBeNull()
    const scrollCalls = spy.mock.calls.filter((call) => call[0] === 'scroll')
    expect(scrollCalls).toEqual([])
    spy.mockRestore()
  })
})
