'use client'

import { useState } from 'react'
import { Button } from '@/components/common/button'
import { ApiError } from '@/lib/api/client'
import { getMe, getRecommendations, savePreferences } from '@/lib/api/commerce'
import { Z } from '@/lib/z'

const USES = ['digoreng', 'dibakar', 'fillet']
const CHARS = ['gurih', 'padat', 'lembut']

export interface PreferencePayload {
  intended_uses: string[]
  characteristics: string[]
}

export interface MatchCount {
  count: number
  profileMissing: boolean
}

// The buyer's own coordinates belong on the account, which the MVP does not
// model. Muara Angke stands in so distance scoring has something to work with.
const DEMO_ORIGIN = { latitude: -6.1, longitude: 106.8 }

async function defaultSave(payload: PreferencePayload): Promise<void> {
  const me = await getMe()
  await savePreferences(me.id, {
    business_type: 'rumah_makan',
    intended_uses: payload.intended_uses,
    characteristics: payload.characteristics,
    ...DEMO_ORIGIN,
  })
}

async function defaultCountMatches(): Promise<MatchCount> {
  const me = await getMe()
  const result = await getRecommendations(me.id)
  return { count: result.items.length, profileMissing: result.profile_missing }
}

export function PreferenceForm({
  initialCount = 0,
  save = defaultSave,
  countMatches = defaultCountMatches,
}: {
  initialCount?: number
  save?: (payload: PreferencePayload) => Promise<void>
  countMatches?: () => Promise<MatchCount>
}) {
  const [uses, setUses] = useState<string[]>([])
  const [chars, setChars] = useState<string[]>([])
  const [count, setCount] = useState(initialCount)
  const [profileMissing, setProfileMissing] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const toggle = (list: string[], setList: (next: string[]) => void, value: string) => {
    setSaved(false)
    setList(list.includes(value) ? list.filter((item) => item !== value) : [...list, value])
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await save({ intended_uses: uses, characteristics: chars })
      setSaved(true)
      // The count comes from the matching engine, not from how many chips are
      // lit: chip arithmetic answers a different question and is always wrong.
      const matches = await countMatches()
      setCount(matches.count)
      setProfileMissing(matches.profileMissing)
    } catch (cause) {
      setSaved(false)
      setError(
        cause instanceof ApiError ? cause.userMessage : 'Gagal menyimpan profil. Coba lagi.'
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="mx-auto flex max-w-[640px] flex-col gap-8 px-4 pb-28" onSubmit={submit}>
      <fieldset>
        <legend className="text-h3 text-ink">Yang dimasak atau dijual</legend>
        <div className="mt-3 flex flex-wrap gap-2">
          {USES.map((use) => (
            <button
              key={use}
              type="button"
              aria-pressed={uses.includes(use)}
              className={`min-h-11 rounded-full border px-4 ${uses.includes(use) ? 'border-ink bg-bg-sunken' : 'border-line'}`}
              onClick={() => toggle(uses, setUses, use)}
            >
              {use}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="text-h3 text-ink">Ciri</legend>
        <div className="mt-3 flex flex-wrap gap-2">
          {CHARS.map((char) => (
            <button
              key={char}
              type="button"
              aria-pressed={chars.includes(char)}
              className={`min-h-11 rounded-full border px-4 ${chars.includes(char) ? 'border-ink bg-bg-sunken' : 'border-line'}`}
              onClick={() => toggle(chars, setChars, char)}
            >
              {char}
            </button>
          ))}
        </div>
      </fieldset>
      <div
        className="fixed inset-x-0 bottom-0 flex items-center justify-between gap-3 border-t border-line bg-surface px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] lg:static lg:border-0 lg:px-0"
        style={{ zIndex: Z.actionBar }}
      >
        <p className="text-num-sm tabular-nums text-ink" aria-live="polite">
          {count} lot cocok
        </p>
        <Button type="submit" loading={busy}>
          Simpan
        </Button>
      </div>
      {profileMissing && (
        <p className="text-body-sm text-ink-muted">
          Belum ada profil pembeli tersimpan. Simpan profil untuk melihat lot yang cocok.
        </p>
      )}
      {error && <p className="text-body-sm text-state-error">{error}</p>}
      {saved && !error && <p className="text-body-sm text-ink-muted">Profil disimpan.</p>}
    </form>
  )
}
