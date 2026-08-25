'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/common/button'
import { Field } from '@/components/common/field'
import { Select } from '@/components/common/select'
import { ApiError } from '@/lib/api/client'
import { getMe, getRecommendations, listLots, savePreferences } from '@/lib/api/commerce'
import { Z } from '@/lib/z'

/** PRD 5.2: the buyer segments the MVP prioritises. */
const BUSINESS_TYPES = [
  { value: 'rumah_makan', label: 'Rumah makan' },
  { value: 'supermarket', label: 'Supermarket' },
  { value: 'peritel_seafood', label: 'Peritel seafood' },
  { value: 'katering', label: 'Katering' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'pengolah', label: 'Pengolah' },
  { value: 'distributor', label: 'Distributor' },
]

const USES = ['digoreng', 'dibakar', 'fillet', 'pindang', 'diasap', 'bakso']
const CHARS = ['gurih', 'padat', 'lembut', 'berminyak', 'daging putih']

export interface PreferencePayload {
  business_type: string
  intended_uses: string[]
  characteristics: string[]
  max_price_per_kg: string
  min_quantity_kg: string
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
    business_type: payload.business_type,
    intended_uses: payload.intended_uses,
    characteristics: payload.characteristics,
    // Sent only when given: an empty box is "no limit", not zero, and zero
    // would match nothing at all.
    max_price_per_kg: payload.max_price_per_kg || undefined,
    min_quantity_kg: payload.min_quantity_kg || undefined,
    ...DEMO_ORIGIN,
  })
}

async function defaultCountMatches(): Promise<MatchCount> {
  const me = await getMe()
  const result = await getRecommendations(me.id)
  return { count: result.items.length, profileMissing: result.profile_missing }
}

/**
 * How many live lots the current draft would reach, before saving anything.
 *
 * Asks the lots endpoint with the draft as filters. Saving first and counting
 * after made every adjustment a blind guess, and the point of the profile is
 * that a buyer can see what each constraint costs them.
 */
/** GET /lots treats repeated `intended_use` / `characteristic` as OR, matching
 *  the engine's set intersection, so the preview predicts the saved count. */
export function previewQuery(payload: PreferencePayload): string {
  const query = new URLSearchParams()
  if (payload.max_price_per_kg) query.set('max_price', payload.max_price_per_kg)
  if (payload.min_quantity_kg) query.set('min_quantity', payload.min_quantity_kg)
  for (const use of payload.intended_uses) query.append('intended_use', use)
  for (const char of payload.characteristics) query.append('characteristic', char)
  return query.toString()
}

async function defaultPreview(payload: PreferencePayload): Promise<number> {
  const lots = await listLots(previewQuery(payload))
  return lots.length
}

export function PreferenceForm({
  initialCount = 0,
  save = defaultSave,
  countMatches = defaultCountMatches,
  preview = defaultPreview,
}: {
  initialCount?: number
  save?: (payload: PreferencePayload) => Promise<void>
  countMatches?: () => Promise<MatchCount>
  preview?: (payload: PreferencePayload) => Promise<number>
}) {
  const [businessType, setBusinessType] = useState(BUSINESS_TYPES[0].value)
  const [uses, setUses] = useState<string[]>([])
  const [chars, setChars] = useState<string[]>([])
  const [maxPrice, setMaxPrice] = useState('')
  const [minVolume, setMinVolume] = useState('')
  const [count, setCount] = useState(initialCount)
  const [previewCount, setPreviewCount] = useState<number | null>(null)
  const [profileMissing, setProfileMissing] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const payload: PreferencePayload = {
    business_type: businessType,
    intended_uses: uses,
    characteristics: chars,
    max_price_per_kg: maxPrice,
    min_quantity_kg: minVolume,
  }
  const key = JSON.stringify(payload)

  useEffect(() => {
    // Debounced: the numeric fields fire on every keystroke, and one request
    // per character would both hammer the API and race its own responses.
    let cancelled = false
    const timer = setTimeout(() => {
      preview(JSON.parse(key))
        .then((next) => {
          if (!cancelled) setPreviewCount(next)
        })
        .catch(() => {
          // A preview is a convenience. Losing it must not break the form.
          if (!cancelled) setPreviewCount(null)
        })
    }, 350)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [key, preview])

  const toggle = (list: string[], setList: (next: string[]) => void, value: string) => {
    setSaved(false)
    setList(list.includes(value) ? list.filter((item) => item !== value) : [...list, value])
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await save(payload)
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
    <form className="mx-auto flex max-w-[640px] flex-col gap-8 pb-28 lg:pb-0" onSubmit={submit}>
      <Select
        label="Jenis usaha"
        helper="Menentukan segmen pembeli yang dicocokkan dengan tiap lot."
        value={businessType}
        onChange={(event) => {
          setSaved(false)
          setBusinessType(event.target.value)
        }}
        options={BUSINESS_TYPES}
      />

      <ChipSet
        legend="Yang dimasak atau dijual"
        hint="Dicocokkan dengan cara olah pada kartu pengetahuan tiap lot."
        options={USES}
        selected={uses}
        onToggle={(value) => toggle(uses, setUses, value)}
      />

      <ChipSet
        legend="Ciri yang dicari"
        hint="Rasa dan tekstur, dicocokkan dengan kartu pengetahuan."
        options={CHARS}
        selected={chars}
        onToggle={(value) => toggle(chars, setChars, value)}
      />

      <fieldset>
        <legend className="text-h3 text-ink">Batas harga dan volume</legend>
        <p className="text-body-sm mt-1 text-ink-muted">
          Kosongkan jika tidak ada batas.
        </p>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <Field
            label="Harga maksimum per kg"
            inputMode="numeric"
            prefix="Rp"
            value={maxPrice}
            onChange={(event) => {
              setSaved(false)
              setMaxPrice(event.target.value)
            }}
          />
          <Field
            label="Volume minimum"
            inputMode="numeric"
            suffix="kg"
            value={minVolume}
            onChange={(event) => {
              setSaved(false)
              setMinVolume(event.target.value)
            }}
          />
        </div>
      </fieldset>

      <div
        className="fixed inset-x-0 bottom-14 flex items-center justify-between gap-3 border-t border-line bg-surface px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] lg:static lg:bottom-auto lg:border-0 lg:px-0"
        style={{ zIndex: Z.actionBar }}
      >
        <div aria-live="polite">
          <p className="text-num-sm tabular-nums text-ink">
            {previewCount ?? count} lot cocok
          </p>
          <p className="text-body-sm text-ink-muted">
            {saved ? 'Profil tersimpan.' : 'Pratinjau, belum disimpan.'}
          </p>
        </div>
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
    </form>
  )
}

function ChipSet({
  legend,
  hint,
  options,
  selected,
  onToggle,
}: {
  legend: string
  hint: string
  options: string[]
  selected: string[]
  onToggle: (value: string) => void
}) {
  return (
    <fieldset>
      <legend className="text-h3 text-ink">{legend}</legend>
      <p className="text-body-sm mt-1 text-ink-muted">{hint}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={selected.includes(option)}
            className={`min-h-11 rounded-full border px-4 transition-colors ${
              selected.includes(option)
                ? 'border-ink bg-bg-sunken text-ink'
                : 'border-line text-ink-muted hover:text-ink'
            }`}
            onClick={() => onToggle(option)}
          >
            {option}
          </button>
        ))}
      </div>
    </fieldset>
  )
}
