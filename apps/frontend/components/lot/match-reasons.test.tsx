import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { REASONS } from '@/test/msw/fixtures'
import { MatchReasons } from './match-reasons'

describe('MatchReasons', () => {
  it('sorts unmet criteria last with a distinct icon and never uses a progressbar', () => {
    const { container } = render(<MatchReasons reasons={REASONS} />)
    const items = screen.getAllByRole('listitem')
    expect(items.at(-1)?.textContent).toMatch(/di luar radius/i)
    expect(container.querySelector('[data-met="false"]')).toBeTruthy()
    expect(container.querySelector('[data-met="true"]')).toBeTruthy()
    expect(container.querySelector('[role="progressbar"]')).toBeNull()
  })
})
