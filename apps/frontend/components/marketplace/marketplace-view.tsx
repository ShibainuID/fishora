'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { Fish, Funnel, Sliders } from '@phosphor-icons/react/dist/ssr'
import { Button } from '@/components/common/button'
import { EmptyState } from '@/components/common/empty-state'
import { LotCard } from '@/components/lot/lot-card'
import { FilterRail } from '@/components/marketplace/filter-rail'
import { FilterSheet } from '@/components/marketplace/filter-sheet'
import {
  activeFilterCount,
  parseFilters,
  serializeFilters,
  type MarketplaceFilters,
} from '@/lib/marketplace-filters'
import { SPECIES } from '@/lib/species'
import type { components } from '@/lib/api/schema'

type Lot = components['schemas']['LotResponse']

export function MarketplaceView({
  lots,
  inventoryEmpty,
}: {
  lots: Lot[]
  inventoryEmpty: boolean
}) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const filters = parseFilters(searchParams.toString())
  const [sheetOpen, setSheetOpen] = useState(false)
  const count = activeFilterCount(filters)

  const apply = (next: MarketplaceFilters) => {
    const query = serializeFilters(next)
    router.replace(query ? `${pathname}?${query}` : pathname)
  }

  const visible = useMemo(() => {
    return lots.filter((lot) => {
      const label = lot.species_id.replace('species_', '')
      if (filters.species.length && !filters.species.includes(label as never)) return false
      if (filters.minPrice && Number(lot.starting_price_per_kg) < Number(filters.minPrice)) return false
      if (filters.maxPrice && Number(lot.starting_price_per_kg) > Number(filters.maxPrice)) return false
      if (filters.minQuantity && Number(lot.quantity_kg) < Number(filters.minQuantity)) return false
      if (filters.maxQuantity && Number(lot.quantity_kg) > Number(filters.maxQuantity)) return false
      return true
    })
  }, [lots, filters])

  return (
    <div className="flex gap-8 pb-24 lg:pb-8">
      <FilterRail filters={filters} onChange={apply} />
      <div className="min-w-0 flex-1">
        <div className="sticky top-14 z-[30] flex items-center gap-2 border-b border-line bg-surface px-4 py-3 lg:static lg:border-0 lg:px-0">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="lg:hidden"
            icon={<Funnel size={16} />}
            onClick={() => setSheetOpen(true)}
          >
            Filters{count ? ` ${count}` : ''}
          </Button>
          <Link
            href={filters.matched ? '/marketplace' : '/marketplace?matched=1'}
            className="text-body-sm min-h-11 px-3 text-ink"
          >
            {filters.matched ? 'Matched for me' : 'All lots'}
          </Link>
          <button type="button" aria-label="Urutkan" className="ml-auto grid size-11 place-items-center lg:hidden">
            <Sliders size={20} />
          </button>
        </div>

        {count > 0 && (
          <div className="flex gap-2 overflow-x-auto px-4 py-3 whitespace-nowrap lg:px-0">
            {filters.species.map((label) => (
              <button
                key={label}
                type="button"
                className="text-body-sm min-h-11 rounded-full border border-line px-3"
                onClick={() => apply({ ...filters, species: filters.species.filter((item) => item !== label) })}
              >
                {SPECIES[label].commonName}
              </button>
            ))}
          </div>
        )}

        {inventoryEmpty ? (
          <EmptyState icon={Fish} message="Belum ada lot aktif." action={<Button type="button">Muat ulang</Button>} />
        ) : visible.length === 0 ? (
          <EmptyState
            icon={Funnel}
            message="Tidak ada lot yang cocok dengan filter ini."
            action={
              <Button type="button" variant="secondary" onClick={() => apply({ ...filters, species: [], minPrice: '', maxPrice: '', minQuantity: '', maxQuantity: '' })}>
                Hapus filter
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 px-4 sm:grid-cols-2 lg:px-0 xl:grid-cols-3">
            {visible.map((lot) => (
              <Link key={lot.id} href={`/marketplace/${lot.id}`}>
                <LotCard
                  lot={lot}
                  photoUrl="/fish/placeholder.jpg"
                  matchPercent={filters.matched ? 0.9 : undefined}
                />
              </Link>
            ))}
          </div>
        )}
      </div>
      <FilterSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        filters={filters}
        onChange={apply}
        resultCount={visible.length}
      />
    </div>
  )
}
