import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { LoginForm } from './login-form'

vi.mock('@/lib/api/commerce', () => ({
  login: vi.fn(),
  logout: vi.fn(),
}))

import { login } from '@/lib/api/commerce'

describe('LoginForm', () => {
  it('signs in with an explicit Save, not autosave, and shows the role name', async () => {
    const user = userEvent.setup()
    vi.mocked(login).mockResolvedValue({
      id: 'op_rian',
      role: 'operator',
      name: 'Rian Setiawan',
      username: 'rian',
    })
    render(<LoginForm />)
    await user.type(screen.getByLabelText(/nama pengguna/i), 'rian')
    await user.type(screen.getByLabelText(/kata sandi/i), 'demo')
    expect(login).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Masuk' }))
    await waitFor(() => {
      expect(login).toHaveBeenCalledWith('rian', 'demo')
    })
    expect(screen.getByText('Rian Setiawan')).toBeInTheDocument()
    expect(screen.getByText(/operator/i)).toBeInTheDocument()
  })
})
