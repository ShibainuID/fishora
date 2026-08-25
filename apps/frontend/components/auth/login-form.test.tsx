import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { LoginForm } from './login-form'

vi.mock('@/lib/api/commerce', () => ({
  login: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

import { login } from '@/lib/api/commerce'

const RIAN = { id: 'op_rian', role: 'operator', name: 'Rian Setiawan', username: 'rian' }
const DEWI = { id: 'buyer_dewi', role: 'buyer', name: 'Dewi Anggraini', username: 'dewi' }

describe('LoginForm', () => {
  it('offers the demo accounts instead of asking for credentials', () => {
    render(<LoginForm />)
    const picker = screen.getByLabelText(/akun demo/i)
    expect(picker.tagName).toBe('SELECT')
    // Credentials that only exist in a source file made this a guessing game.
    expect(screen.queryByLabelText(/kata sandi/i)).not.toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Rian Setiawan/ })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /Dewi Anggraini/ })).toBeInTheDocument()
  })

  it('signs in with an explicit submit, not on selection', async () => {
    const user = userEvent.setup()
    vi.mocked(login).mockResolvedValue(RIAN)
    render(<LoginForm />)

    await user.selectOptions(screen.getByLabelText(/akun demo/i), 'rian')
    expect(login).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: /masuk sebagai rian setiawan/i }))
    await waitFor(() => expect(login).toHaveBeenCalledWith('rian', 'demo'))
    expect(screen.getByText('Rian Setiawan')).toBeInTheDocument()
    expect(screen.getByText(/operator/i)).toBeInTheDocument()
  })

  it('sends the credentials of the account actually chosen', async () => {
    const user = userEvent.setup()
    vi.mocked(login).mockResolvedValue(DEWI)
    render(<LoginForm />)

    await user.selectOptions(screen.getByLabelText(/akun demo/i), 'dewi')
    await user.click(screen.getByRole('button', { name: /masuk sebagai dewi anggraini/i }))

    await waitFor(() => expect(login).toHaveBeenCalledWith('dewi', 'demo'))
    expect(screen.getByText(/pembeli/i)).toBeInTheDocument()
  })

  it('reports a failed sign-in instead of appearing to succeed', async () => {
    const user = userEvent.setup()
    vi.mocked(login).mockRejectedValue(new Error('nope'))
    render(<LoginForm />)

    await user.click(screen.getByRole('button', { name: /masuk sebagai/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/gagal masuk/i))
  })
})
