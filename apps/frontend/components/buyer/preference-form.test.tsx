import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { PreferenceForm } from './preference-form'

describe('PreferenceForm', () => {
  it('updates the live match count on change and saves only on submit', async () => {
    const onSave = vi.fn()
    const user = userEvent.setup()
    render(<PreferenceForm initialCount={4} onSave={onSave} />)
    expect(screen.getByText('4 lots match')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'digoreng' }))
    expect(screen.getByText('5 lots match')).toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(onSave).toHaveBeenCalledTimes(1)
    const bar = screen.getByRole('button', { name: 'Save' }).closest('div')
    expect(bar?.className).toContain('fixed')
  })
})
