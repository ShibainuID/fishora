import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, type Mock } from 'vitest'
import { PreferenceForm } from './preference-form'

// Typed as concrete mocks, not as the prop union, so `.mock` is reachable.
function seams(overrides: { save?: Mock; countMatches?: Mock } = {}) {
  return {
    save: vi.fn().mockResolvedValue(undefined),
    countMatches: vi.fn().mockResolvedValue({ count: 7, profileMissing: false }),
    ...overrides,
  }
}

describe('PreferenceForm', () => {
  it('saves only on submit, never on a chip change', async () => {
    const user = userEvent.setup()
    const props = seams()
    render(<PreferenceForm {...props} />)

    await user.click(screen.getByRole('button', { name: 'digoreng' }))
    expect(props.save).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Simpan' }))
    expect(props.save).toHaveBeenCalledTimes(1)
    expect(props.save.mock.calls[0][0]).toEqual({
      intended_uses: ['digoreng'],
      characteristics: [],
    })
  })

  it('shows the count the API returns, not the number of chips picked', async () => {
    const user = userEvent.setup()
    const props = seams({
      countMatches: vi.fn().mockResolvedValue({ count: 2, profileMissing: false }),
    })
    render(<PreferenceForm initialCount={9} {...props} />)

    // Three chips would make chip arithmetic say 12. The real answer is 2.
    await user.click(screen.getByRole('button', { name: 'digoreng' }))
    await user.click(screen.getByRole('button', { name: 'dibakar' }))
    await user.click(screen.getByRole('button', { name: 'gurih' }))
    await user.click(screen.getByRole('button', { name: 'Simpan' }))

    await waitFor(() => expect(screen.getByText(/^2 lot cocok$/)).toBeInTheDocument())
    expect(screen.queryByText(/12 lot/)).not.toBeInTheDocument()
  })

  it('refetches the count after saving', async () => {
    const user = userEvent.setup()
    const props = seams()
    render(<PreferenceForm {...props} />)
    await user.click(screen.getByRole('button', { name: 'Simpan' }))
    await waitFor(() => expect(props.countMatches).toHaveBeenCalledTimes(1))
  })

  it('prompts to set a profile when the API reports none', async () => {
    const user = userEvent.setup()
    const props = seams({
      countMatches: vi.fn().mockResolvedValue({ count: 0, profileMissing: true }),
    })
    render(<PreferenceForm {...props} />)
    await user.click(screen.getByRole('button', { name: 'Simpan' }))
    await waitFor(() =>
      expect(screen.getByText(/belum ada profil/i)).toBeInTheDocument()
    )
  })

  it('surfaces a save failure instead of claiming success', async () => {
    const user = userEvent.setup()
    const props = seams({ save: vi.fn().mockRejectedValue(new Error('nope')) })
    render(<PreferenceForm {...props} />)
    await user.click(screen.getByRole('button', { name: 'Simpan' }))
    await waitFor(() => expect(screen.getByText(/gagal/i)).toBeInTheDocument())
    expect(screen.queryByText(/profil disimpan/i)).not.toBeInTheDocument()
  })

  it('keeps the action bar fixed on phones', () => {
    render(<PreferenceForm {...seams()} />)
    const bar = screen.getByRole('button', { name: 'Simpan' }).closest('div')
    expect(bar?.className).toContain('fixed')
  })
})
