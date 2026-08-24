import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Countdown } from './countdown'

describe('Countdown', () => {
  it('renders from a server timestamp and uses the warn token under five minutes', () => {
    const endsAt = '2026-08-24T10:04:00+00:00'
    const now = Date.parse('2026-08-24T10:00:00+00:00')
    const { rerender } = render(<Countdown endsAt={endsAt} now={now} />)
    const time = screen.getByRole('time')
    expect(time).toHaveTextContent('4:00')
    expect(time.className).toContain('text-state-warn')

    rerender(<Countdown endsAt="2026-08-24T12:00:00+00:00" now={now} />)
    expect(screen.getByRole('time').className).not.toContain('text-state-warn')
  })
})
