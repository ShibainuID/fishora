import { MarketplaceView } from '@/components/marketplace/marketplace-view'
import { listLots } from '@/lib/api/commerce'

export default async function MarketplacePage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}) {
  const params = await searchParams
  const query = new URLSearchParams()
  const species = typeof params.species === 'string' ? params.species.split(',')[0] : undefined
  if (species) query.set('species_id', `species_${species}`)
  if (typeof params.min_price === 'string') query.set('min_price', params.min_price)
  if (typeof params.max_price === 'string') query.set('max_price', params.max_price)
  if (typeof params.min_qty === 'string') query.set('min_quantity', params.min_qty)
  if (typeof params.max_qty === 'string') query.set('max_quantity', params.max_qty)
  query.set('status', 'active')

  let lots = []
  try {
    lots = await listLots(query.toString())
  } catch {
    lots = []
  }

  return <MarketplaceView lots={lots} inventoryEmpty={lots.length === 0 && !query.get('species_id')} />
}
