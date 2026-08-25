import { ShieldCheck } from '@phosphor-icons/react/dist/ssr'
import { resolveSpecies } from '@/lib/species'

// Unknown labels render as-is, so a model update cannot white-screen the operator.
export interface SpeciesHeaderProps {
  label: string
  /** Overrides the map when the card already carries a scientific name. */
  scientificName?: string | null
  verified?: boolean
}

export function SpeciesHeader({
  label,
  scientificName,
  verified = false,
}: SpeciesHeaderProps) {
  const resolved = resolveSpecies(label)
  const sci = scientificName === undefined ? resolved.scientificName : scientificName

  return (
    <header className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-h1 text-ink">{resolved.commonName}</h2>
        {verified && (
          <span className="text-body-sm inline-flex items-center gap-1.5 text-verified">
            <ShieldCheck className="size-4" weight="fill" aria-hidden />
            Terverifikasi
          </span>
        )}
      </div>
      {sci && (
        <p className="text-body max-w-[65ch] text-ink-muted italic">{sci}</p>
      )}
    </header>
  )
}
