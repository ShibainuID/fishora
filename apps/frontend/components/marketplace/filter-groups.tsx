'use client'

import { SPECIES, SUPPORTED_LABELS, type SpeciesLabel } from '@/lib/species'
import type { MarketplaceFilters } from '@/lib/marketplace-filters'

export function FilterGroups({
  filters,
  onChange,
  defaultOpen = false,
}: {
  filters: MarketplaceFilters
  onChange: (next: MarketplaceFilters) => void
  defaultOpen?: boolean
}) {
  const toggleSpecies = (label: SpeciesLabel) => {
    const species = filters.species.includes(label)
      ? filters.species.filter((item) => item !== label)
      : [...filters.species, label]
    onChange({ ...filters, species })
  }

  return (
    <div className="flex flex-col">
      <fieldset className="border-t border-line py-4">
        <details open>
          <summary className="text-label cursor-pointer text-ink">Spesies</summary>
          <div className="mt-3 flex flex-wrap gap-2">
            {SUPPORTED_LABELS.map((label) => (
              <label key={label} className="text-body-sm flex min-h-11 items-center gap-2 text-ink">
                <input
                  type="checkbox"
                  checked={filters.species.includes(label)}
                  onChange={() => toggleSpecies(label)}
                />
                {SPECIES[label].commonName}
              </label>
            ))}
          </div>
        </details>
      </fieldset>
      <fieldset className="border-t border-line py-4">
        <details open>
          <summary className="text-label cursor-pointer text-ink">Harga</summary>
          <div className="mt-3 flex gap-2">
            <input
              aria-label="Harga minimum"
              className="min-h-11 w-full rounded-[var(--radius-input)] border border-line-input px-3 text-ink"
              value={filters.minPrice}
              onChange={(event) => onChange({ ...filters, minPrice: event.target.value })}
            />
            <input
              aria-label="Harga maksimum"
              className="min-h-11 w-full rounded-[var(--radius-input)] border border-line-input px-3 text-ink"
              value={filters.maxPrice}
              onChange={(event) => onChange({ ...filters, maxPrice: event.target.value })}
            />
          </div>
        </details>
      </fieldset>
      <fieldset className="border-t border-line py-4">
        <details open={defaultOpen}>
          <summary className="text-label cursor-pointer text-ink">Volume</summary>
          <div className="mt-3 flex gap-2">
            <input
              aria-label="Volume minimum"
              className="min-h-11 w-full rounded-[var(--radius-input)] border border-line-input px-3 text-ink"
              value={filters.minQuantity}
              onChange={(event) => onChange({ ...filters, minQuantity: event.target.value })}
            />
            <input
              aria-label="Volume maksimum"
              className="min-h-11 w-full rounded-[var(--radius-input)] border border-line-input px-3 text-ink"
              value={filters.maxQuantity}
              onChange={(event) => onChange({ ...filters, maxQuantity: event.target.value })}
            />
          </div>
        </details>
      </fieldset>
      <fieldset className="border-t border-line py-4">
        <legend className="text-label text-ink">Radius layanan 100 km</legend>
        <p className="text-body-sm mt-2 text-ink-muted">
          Jarak adalah proksi layanan, bukan klaim kesegaran.
        </p>
      </fieldset>
    </div>
  )
}
