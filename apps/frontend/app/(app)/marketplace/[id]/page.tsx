import { LotDetail } from '@/components/lot/lot-detail'
import { getDiscover, getLot, listReviews, type Review } from '@/lib/api/commerce'
import { getMeAsServer } from '@/lib/api/server'
import type { KnowledgeCard } from '@/lib/api/fish'

const EMPTY_CARD: KnowledgeCard = {
  common_name: '',
  scientific_name: null,
  taxonomy_status: 'VERIFIED_TAXONOMY',
  physical_characteristics: null,
  taste: null,
  texture: null,
  processing_methods: [],
  commercial_uses: [],
  similar_or_substitute_species: [],
  potential_buyer_segments: [],
  limitations: [],
  sources: [],
}

export default async function LotPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const lot = await getLot(id)
  let card = EMPTY_CARD
  try {
    card = (await getDiscover(lot.public_slug)).card
  } catch {
    // Snapshot is optional on a live lot that has not finished generation.
  }

  // Fetch first, render after: JSX built inside a try/catch is not protected.
  let reviews: Review[] = []
  try {
    reviews = await listReviews(id)
  } catch {
    // A missing signal list must not take the lot page down with it.
  }

  let canReview = false
  try {
    const me = await getMeAsServer()
    canReview = me.role === 'buyer' && lot.allocated_buyer_id === me.id
  } catch {
    // Anonymous or expired session: the list alone, with no form.
  }

  return (
    <LotDetail
      lot={lot}
      card={card}
      reasons={[]}
      reviews={reviews}
      canReview={canReview}
    />
  )
}
