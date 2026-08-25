import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi, type Mock } from 'vitest'
import { PreferenceForm } from './preference-form'

// Typed as concrete mocks, not as the prop union, so `.mock` is reachable.
function seams(overrides: { save?: Mock; countMatches?: Mock; preview?: Mock } = {}) {
  return {
    save: vi.fn().mockResolvedValue(undefined),
    countMatches: vi.fn().mockResolvedValue({ count: 7, profileMissing: false }),
    // Stubbed by default: the live preview fires on every edit, and an
    // unstubbed one would put a real request behind every test.
    preview: vi.fn().mockResolvedValue(0),
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
      business_type: 'rumah_makan',
      intended_uses: ['digoreng'],
      characteristics: [],
      max_price_per_kg: '',
      min_quantity_kg: '',
    })
  })

  it('sends the whole PRD profile, not just the chips', async () => {
    const user = userEvent.setup()
    const props = seams()
    render(<PreferenceForm {...props} />)

    await user.selectOptions(screen.getByLabelText(/jenis usaha/i), 'katering')
    await user.type(screen.getByLabelText(/harga maksimum/i), '70000')
    await user.type(screen.getByLabelText(/volume minimum/i), '20')
    await user.click(screen.getByRole('button', { name: 'fillet' }))
    await user.click(screen.getByRole('button', { name: 'padat' }))
    await user.click(screen.getByRole('button', { name: 'Simpan' }))

    // Business type used to be hardcoded and the limits were never sent at all,
    // so a buyer's price ceiling had no effect on what they were shown.
    expect(props.save.mock.calls[0][0]).toEqual({
      business_type: 'katering',
      intended_uses: ['fillet'],
      characteristics: ['padat'],
      max_price_per_kg: '70000',
      min_quantity_kg: '20',
    })
  })

  it('previews the reach of a draft before it is saved', async () => {
    const user = userEvent.setup()
    const props = seams({ preview: vi.fn().mockResolvedValue(3) })
    render(<PreferenceForm initialCount={9} {...props} />)

    await user.click(screen.getByRole('button', { name: 'digoreng' }))

    await waitFor(() => expect(screen.getByText(/^3 lot cocok$/)).toBeInTheDocument())
    // The count has to be labelled as a draft, or it reads as saved state.
    expect(screen.getByText(/belum disimpan/i)).toBeInTheDocument()
    expect(props.save).not.toHaveBeenCalled()
  })

  it('survives a preview failure instead of breaking the form', async () => {
    const user = userEvent.setup()
    const props = seams({ preview: vi.fn().mockRejectedValue(new Error('offline')) })
    render(<PreferenceForm {...props} />)

    await user.click(screen.getByRole('button', { name: 'digoreng' }))
    await user.click(screen.getByRole('button', { name: 'Simpan' }))

    await waitFor(() => expect(props.save).toHaveBeenCalledTimes(1))
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
    await waitFor(() => expect(screen.getByText(/belum ada profil/i)).toBeInTheDocument())
  })

  it('surfaces a save failure instead of claiming success', async () => {
    const user = userEvent.setup()
    const props = seams({ save: vi.fn().mockRejectedValue(new Error('nope')) })
    render(<PreferenceForm {...props} />)
    await user.click(screen.getByRole('button', { name: 'Simpan' }))
    await waitFor(() => expect(screen.getByText(/gagal/i)).toBeInTheDocument())
    expect(screen.queryByText(/profil tersimpan/i)).not.toBeInTheDocument()
  })

  it('keeps the action bar fixed on phones', () => {
    render(<PreferenceForm {...seams()} />)
    const bar = screen.getByRole('button', { name: 'Simpan' }).closest('div')
    expect(bar?.className).toContain('fixed')
  })
})
