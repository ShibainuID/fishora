'use client'

import { useState } from 'react'
import { MagnifyingGlass } from '@phosphor-icons/react/dist/ssr'
import { Button } from '@/components/common/button'
import { Field } from '@/components/common/field'
import { Skeleton } from '@/components/common/skeleton'
import type { ActionResult } from '@/lib/api/action-result'
import type { NameMatch, SpeciesLookupResult, UnlistedFields } from '@/lib/api/fish'

function host(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

/**
 * For a catch outside the 11 trained species. The operator types the name it
 * is sold under; a web lookup proposes scientific names, each tied to a source
 * that names both, and the operator picks one or lists the fish by its local
 * name alone. Either way the species is marked for expert review.
 */
export function UnlistedSpecies({
  busy,
  onLookup,
  onDeclare,
}: {
  busy: boolean
  onLookup: (localName: string) => Promise<ActionResult<SpeciesLookupResult>>
  onDeclare: (fields: UnlistedFields) => void
}) {
  const [name, setName] = useState('')
  const [status, setStatus] = useState<'idle' | 'searching' | 'done' | 'failed'>('idle')
  const [result, setResult] = useState<SpeciesLookupResult | null>(null)
  const [message, setMessage] = useState('')

  const trimmed = name.trim()
  // The name the results belong to; editing the field invalidates them.
  const searched = result?.local_name ?? trimmed

  async function search() {
    if (!trimmed) return
    setStatus('searching')
    setResult(null)
    const found = await onLookup(trimmed)
    if (found.ok) {
      setResult(found.data)
      setStatus('done')
    } else {
      setMessage(found.status === 422 ? found.userMessage : 'The lookup is unavailable right now.')
      setStatus('failed')
    }
  }

  function pick(match: NameMatch) {
    onDeclare({ localName: searched, scientificName: match.scientific_name, rank: match.rank, sourceUrl: match.url })
  }

  return (
    <section aria-labelledby="unlisted-heading" className="flex flex-col gap-3 rounded-2xl border border-line px-4 py-4">
      <div>
        <h3 id="unlisted-heading" className="text-label text-ink">
          Not in this list?
        </h3>
        <p className="text-body-sm text-ink-muted">
          Type the name the fish is sold under. We look it up on FishBase, FAO and Wikipedia.
        </p>
      </div>

      <form
        className="flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          void search()
        }}
      >
        <Field
          label="Local name"
          placeholder="e.g. baronang"
          value={name}
          maxLength={60}
          onChange={(event) => {
            setName(event.target.value)
            if (status !== 'searching') {
              setStatus('idle')
              setResult(null)
            }
          }}
        />
        <Button type="submit" variant="secondary" block loading={status === 'searching'} disabled={!trimmed || busy}>
          <MagnifyingGlass className="size-4" aria-hidden />
          Look up
        </Button>
      </form>

      {status === 'searching' && (
        <div className="flex flex-col gap-2" aria-live="polite">
          <p className="text-body-sm text-ink-muted">Searching, this takes about ten seconds…</p>
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      )}

      {status === 'failed' && <p className="text-body-sm text-state-warn">{message}</p>}

      {status === 'done' && result && result.candidates.length === 0 && (
        <p className="text-body-sm text-ink-muted">No source links &ldquo;{searched}&rdquo; to a scientific name.</p>
      )}

      {status === 'done' && result && result.candidates.length > 0 && (
        <ul className="flex flex-col gap-2" aria-label="Possible species">
          {result.candidates.map((match) => (
            <li key={match.scientific_name} className="flex flex-col gap-2 rounded-xl border border-line px-3 py-3">
              <div className="flex flex-col gap-0.5">
                <span className="text-body text-ink italic">{match.scientific_name}</span>
                {match.english_name && <span className="text-body-sm text-ink-muted">{match.english_name}</span>}
                <a
                  href={match.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-body-sm text-ink-muted underline underline-offset-2"
                >
                  Source: {host(match.url)}
                </a>
                {match.existing_species_id && (
                  <span className="text-body-sm text-verified">Already listed in Fishora; the catch joins it.</span>
                )}
              </div>
              <Button size="md" block disabled={busy} onClick={() => pick(match)}>
                This is my fish
              </Button>
            </li>
          ))}
        </ul>
      )}

      {(status === 'done' || status === 'failed') && searched && (
        <div className="flex flex-col gap-1">
          <Button variant="ghost" block disabled={busy} onClick={() => onDeclare({ localName: searched })}>
            List it as &ldquo;{searched}&rdquo; without a scientific name
          </Button>
          <p className="text-body-sm text-ink-muted">
            New species are marked for expert review and start with an empty knowledge card.
          </p>
        </div>
      )}
    </section>
  )
}
