'use client'

import { useState } from 'react'
import { Button } from '@/components/common/button'
import { Field } from '@/components/common/field'
import { login, logout } from '@/lib/api/commerce'
import { ApiError } from '@/lib/api/errors'

type Session = { id: string; role: string; name: string; username: string }

export function LoginForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [session, setSession] = useState<Session | null>(null)

  async function submit() {
    setBusy(true)
    setError('')
    try {
      setSession(await login(username, password))
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.userMessage : 'Gagal masuk.')
    } finally {
      setBusy(false)
    }
  }

  if (session) {
    return (
      <div className="mt-6 flex flex-col gap-3">
        <p className="text-h3 text-ink">{session.name}</p>
        <p className="text-body-sm text-ink-muted">{session.role}</p>
        <Button
          type="button"
          variant="secondary"
          onClick={async () => {
            await logout()
            setSession(null)
          }}
        >
          Keluar
        </Button>
      </div>
    )
  }

  return (
    <form
      className="mt-6 flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault()
        void submit()
      }}
    >
      <Field
        label="Nama pengguna"
        autoComplete="username"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
      />
      <Field
        label="Kata sandi"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        error={error || undefined}
      />
      <p className="text-body-sm text-ink-muted">
        Demo: rian (operator) atau dewi (pembeli), kata sandi demo.
      </p>
      <Button type="submit" block loading={busy}>
        Masuk
      </Button>
    </form>
  )
}
