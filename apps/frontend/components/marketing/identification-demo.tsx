'use client'

import { useState } from 'react'
import { PredictionCard } from '@/components/fish/prediction-card'
import type { IdentificationResult } from '@/lib/api/fish'
import { resolveSpecies } from '@/lib/species'

// A client leaf so the landing page stays a Server Component. It is also the
// real component with real state, not a screenshot of one.
export function IdentificationDemo({ result }: { result: IdentificationResult }) {
  const [confirmed, setConfirmed] = useState<string | null>(null)

  return (
    <div className="flex flex-col gap-3">
      <PredictionCard result={result} onConfirm={setConfirmed} />
      {confirmed && (
        <p className="text-body-sm text-ink-muted" aria-live="polite">
          Verified as {resolveSpecies(labelFor(result, confirmed)).commonName}.
        </p>
      )}
    </div>
  )
}

function labelFor(result: IdentificationResult, speciesId: string): string {
  const match = result.top_candidates.find((c) => c.species_id === speciesId)
  return match?.normalized_label ?? result.prediction.normalized_label
}
