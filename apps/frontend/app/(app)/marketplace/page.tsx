import { MarketplaceView } from '@/components/marketplace/marketplace-view'
import { listLots, type Lot } from '@/lib/api/commerce'
import { getMeAsServer, getRecommendationsAsServer } from '@/lib/api/server'

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

  const wantsMatched = params.matched === '1'

  if (wantsMatched) {
    // Ordered by score by the matching engine, so the grid keeps that order
    // rather than re-sorting client-side. Fetch first, render after: JSX built
    // inside a try/catch is not actually protected by it.
    let matchedLots: Lot[] = []
    let matchScores: Record<string, number> = {}
    let profileMissing = true
    try {
      const me = await getMeAsServer()
      const recommendations = await getRecommendationsAsServer(me.id)
      matchedLots = recommendations.items.map((item) => item.lot)
      matchScores = Object.fromEntries(
        recommendations.items.map((item) => [item.lot.id, item.score])
      )
      profileMissing = recommendations.profile_missing
    } catch {
      // Not signed in, or no profile yet. Prompting for one is honest; falling
      // back to the open grid would present unmatched lots as matches.
      profileMissing = true
    }
    return (
      <MarketplaceView
        lots={matchedLots}
        inventoryEmpty={false}
        matched
        matchScores={matchScores}
        profileMissing={profileMissing}
      />
    )
  }

  let lots: Lot[] = []
  try {
    lots = await listLots(query.toString())
  } catch {
    lots = []
  }

  return <MarketplaceView lots={lots} inventoryEmpty={lots.length === 0 && !query.get('species_id')} />
}
