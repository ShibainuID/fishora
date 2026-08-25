'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { Button } from '@/components/common/button'
import { login, logout } from '@/lib/api/commerce'
import { ApiError } from '@/lib/api/errors'

type Session = { id: string; role: string; name: string; username: string }

/**
 * The seeded demo accounts, from apps/main_api/services/session.py.
 *
 * A free-text username and password asked people to know credentials that only
 * exist in a source file, so the sign-in screen was a guessing game. These are
 * demo accounts on a demo deployment; listing them is the point.
 */
const DEMO_ACCOUNTS = [
  {
    username: 'rian',
    password: 'demo',
    name: 'Rian Setiawan',
    role: 'Operator',
    blurb: 'Identifikasi tangkapan dan terbitkan lot.',
  },
  {
    username: 'dewi',
    password: 'demo',
    name: 'Dewi Anggraini',
    role: 'Pembeli',
    blurb: 'Telusuri lelang, ajukan penawaran, tulis ulasan.',
  },
] as const

export function LoginForm({ initialSession = null }: { initialSession?: Session | null }) {
  const router = useRouter()
  const [username, setUsername] = useState<string>(DEMO_ACCOUNTS[0].username)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [session, setSession] = useState<Session | null>(initialSession)

  const chosen = DEMO_ACCOUNTS.find((account) => account.username === username) ?? DEMO_ACCOUNTS[0]

  async function submit() {
    setBusy(true)
    setError('')
    try {
      setSession(await login(chosen.username, chosen.password))
      // The shell reads the session on the server, so it only picks up the new
      // role once the tree is refetched.
      router.refresh()
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
        <p className="text-body-sm text-ink-muted">
          Masuk sebagai {session.role === 'operator' ? 'operator' : 'pembeli'}.
        </p>
        <Button
          type="button"
          variant="secondary"
          onClick={async () => {
            await logout()
            setSession(null)
            router.refresh()
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
      <div className="flex flex-col gap-2">
        <label htmlFor="demo-account" className="text-label text-ink-muted">
          Akun demo
        </label>
        <select
          id="demo-account"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          className="text-body min-h-11 w-full rounded-[var(--radius-input)] border border-line-input bg-transparent px-3 text-ink outline-none focus-visible:border-ink"
        >
          {DEMO_ACCOUNTS.map((account) => (
            <option key={account.username} value={account.username}>
              {account.name} ({account.role})
            </option>
          ))}
        </select>
        <p className="text-body-sm text-ink-muted">{chosen.blurb}</p>
      </div>

      {error && (
        <p className="text-body-sm text-state-error" role="alert">
          {error}
        </p>
      )}

      <Button type="submit" block loading={busy}>
        Masuk sebagai {chosen.name}
      </Button>
    </form>
  )
}
