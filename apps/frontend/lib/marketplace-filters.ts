import { SUPPORTED_LABELS, type SpeciesLabel } from '@/lib/species'

export interface MarketplaceFilters {
  species: SpeciesLabel[]
  minPrice: string
  maxPrice: string
  minQuantity: string
  maxQuantity: string
  matched: boolean
}

export const EMPTY_FILTERS: MarketplaceFilters = {
  species: [],
  minPrice: '',
  maxPrice: '',
  minQuantity: '',
  maxQuantity: '',
  matched: false,
}

export function parseFilters(search: string): MarketplaceFilters {
  const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : search)
  const species = (params.get('species') ?? '')
    .split(',')
    .filter((label): label is SpeciesLabel =>
      (SUPPORTED_LABELS as readonly string[]).includes(label)
    )
  return {
    species,
    minPrice: params.get('min_price') ?? '',
    maxPrice: params.get('max_price') ?? '',
    minQuantity: params.get('min_qty') ?? '',
    maxQuantity: params.get('max_qty') ?? '',
    matched: params.get('matched') === '1',
  }
}

export function serializeFilters(filters: MarketplaceFilters): string {
  const params = new URLSearchParams()
  if (filters.species.length) params.set('species', filters.species.join(','))
  if (filters.minPrice) params.set('min_price', filters.minPrice)
  if (filters.maxPrice) params.set('max_price', filters.maxPrice)
  if (filters.minQuantity) params.set('min_qty', filters.minQuantity)
  if (filters.maxQuantity) params.set('max_qty', filters.maxQuantity)
  if (filters.matched) params.set('matched', '1')
  return params.toString()
}

export function activeFilterCount(filters: MarketplaceFilters): number {
  return [
    filters.species.length > 0,
    Boolean(filters.minPrice || filters.maxPrice),
    Boolean(filters.minQuantity || filters.maxQuantity),
  ].filter(Boolean).length
}
