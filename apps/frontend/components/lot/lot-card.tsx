import Image from 'next/image'
import { Countdown } from '@/components/lot/countdown'
import { kilograms, percent, rupiahPerKg } from '@/lib/format'
import { resolveSpecies } from '@/lib/species'
import { SpeciesArt } from '@/components/fish/species-art'
import type { components } from '@/lib/api/schema'

export type Lot = components['schemas']['LotResponse']

export interface LotCardProps {
  lot: Lot
  /** A real photograph when one exists. Falls back to the species composition. */
  photoUrl?: string
  /** Set on the first card in a grid: it is the LCP element. */
  priority?: boolean
  /** Only passed from the matched view. */
  matchPercent?: number
}

export function LotCard({ lot, photoUrl, matchPercent, priority = false }: LotCardProps) {
  const label = lot.species_id.replace('species_', '')
  const names = resolveSpecies(label)
  const live = lot.status === 'active'

  return (
    <article className="flex flex-col gap-3 lg:transition-transform lg:hover:-translate-y-[2px]">
      <div className="relative aspect-[4/3] overflow-hidden rounded-[var(--radius-card)] bg-bg-sunken">
        {photoUrl ? (
          <Image src={photoUrl} alt={names.commonName} fill className="object-cover" sizes="(max-width: 640px) 100vw, 33vw" />
        ) : (
          <SpeciesArt label={label} className="absolute inset-0" priority={priority} />
        )}
      </div>
      <div className="flex flex-col gap-1 px-1">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-h3 text-ink">{names.commonName}</h2>
          {live ? (
            <p className="text-body-sm flex items-center gap-1.5 text-ink">
              <span className="size-1.5 rounded-full bg-accent" aria-hidden />
              Berlangsung
            </p>
          ) : (
            <p className="text-body-sm text-ink-muted">Selesai</p>
          )}
        </div>
        {matchPercent != null && (
          <p className="text-num-sm tabular-nums text-ink">{percent(matchPercent)} cocok</p>
        )}
        <p className="text-num-sm tabular-nums text-ink-muted">{kilograms(Number(lot.quantity_kg))}</p>
        <p className="text-num-sm tabular-nums text-ink">
          {rupiahPerKg(Number(lot.current_highest_per_kg ?? lot.starting_price_per_kg))}
        </p>
        {live && <Countdown endsAt={lot.auction_ends_at} />}
      </div>
    </article>
  )
}
