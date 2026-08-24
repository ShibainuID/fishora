import { LotDetail } from '@/components/lot/lot-detail'
import { getDiscover, getLot } from '@/lib/api/commerce'
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
  return (
    <LotDetail
      lot={lot}
      card={card}
      reasons={[]}
      signals={[{ businessType: 'Rumah Makan Cendana', useCase: 'Digoreng' }]}
      photoUrl="/fish/placeholder.jpg"
    />
  )
}
