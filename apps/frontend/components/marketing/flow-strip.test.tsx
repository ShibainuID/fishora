import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FlowStrip } from './flow-strip'

describe('FlowStrip', () => {
  it('is a native swipe strip without JS-only controls', () => {
    const { container } = render(<FlowStrip />)
    const strip = container.querySelector('#flow')
    expect(strip?.className).toContain('overflow-x-auto')
    expect(strip?.className).toContain('snap-x')
    expect(container.querySelectorAll('article')).toHaveLength(8)
  })
})
