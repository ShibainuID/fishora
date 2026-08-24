'use client'

import { useState } from 'react'
import { Button } from '@/components/common/button'
import { Z } from '@/lib/z'

const USES = ['digoreng', 'dibakar', 'fillet']
const CHARS = ['gurih', 'padat', 'lembut']

export function PreferenceForm({
  initialCount = 0,
  onSave,
}: {
  initialCount?: number
  onSave: (payload: { intended_uses: string[]; characteristics: string[] }) => Promise<void> | void
}) {
  const [uses, setUses] = useState<string[]>([])
  const [chars, setChars] = useState<string[]>([])
  const [saved, setSaved] = useState(false)
  const matchCount = initialCount + uses.length + chars.length

  const toggle = (list: string[], setList: (next: string[]) => void, value: string) => {
    setSaved(false)
    setList(list.includes(value) ? list.filter((item) => item !== value) : [...list, value])
  }

  return (
    <form
      className="mx-auto flex max-w-[640px] flex-col gap-8 px-4 pb-28"
      onSubmit={async (event) => {
        event.preventDefault()
        await onSave({ intended_uses: uses, characteristics: chars })
        setSaved(true)
      }}
    >
      <fieldset>
        <legend className="text-h3 text-ink">Yang dimasak atau dijual</legend>
        <div className="mt-3 flex flex-wrap gap-2">
          {USES.map((use) => (
            <button
              key={use}
              type="button"
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
        <p className="text-num-sm tabular-nums text-ink">{matchCount} lots match</p>
        <Button type="submit">Save</Button>
      </div>
      {saved && <p className="text-body-sm text-ink-muted">Profil disimpan.</p>}
    </form>
  )
}
