import type { components } from '@/lib/api/schema'
import { SUPPORTED_LABELS } from '@/lib/species'

export type Lot = components['schemas']['LotResponse']
export type Bid = components['schemas']['BidResponse']
export type KnowledgeCard = components['schemas']['KnowledgeCard']
export type MatchReason = components['schemas']['MatchReasonResponse']

// mock: demo businesses and people from DESIGN.md 13
export const BUYERS = {
  pasar: 'Pasar Segar Nusantara',
  cendana: 'Rumah Makan Cendana',
  prima: 'Sentra Boga Prima',
} as const

export const PEOPLE = {
  operator: 'Rian Setiawan',
  buyer: 'Dewi Anggraini',
} as const

export const ALL_SPECIES_IDS = SUPPORTED_LABELS.map((label) => `species_${label}`)

const START = '2026-08-24T10:00:00+00:00'
const END = '2026-08-24T14:00:00+00:00'
const CLOSED_END = '2026-08-24T09:00:00+00:00'

export function lotFixture(overrides: Partial<Lot> = {}): Lot {
  return {
    id: 'lot_tenggiri_1',
    prediction_id: 'pred_ok',
    operator_id: 'op_rian',
    species_id: 'species_tenggiri',
    landing_point_id: 'lp_muara_angke',
    quantity_kg: '24.000',
    size_category: 'L',
    starting_price_per_kg: '68000.00',
    status: 'active',
    auction_starts_at: START,
    auction_ends_at: END,
    public_slug: 'tenggiri-lot1',
    allocated_buyer_id: null,
    current_highest_per_kg: '70000.00',
    serviceability_radius_km: 100,
    ...overrides,
  }
}

export const LOTS: Lot[] = [
  lotFixture(),
  lotFixture({
    id: 'lot_kembung_1',
    species_id: 'species_kembung',
    public_slug: 'kembung-lot1',
    quantity_kg: '18.000',
    starting_price_per_kg: '42000.00',
    current_highest_per_kg: '42000.00',
  }),
  lotFixture({
    id: 'lot_tuna_closed',
    species_id: 'species_tuna',
    public_slug: 'tuna-closed',
    status: 'closed',
    auction_ends_at: CLOSED_END,
    current_highest_per_kg: '91000.00',
  }),
]

export const BIDS: Bid[] = [
  {
    id: 'bid_1',
    lot_id: 'lot_tenggiri_1',
    buyer_id: 'buyer_dewi',
    amount_per_kg: '70000.00',
    created_at: '2026-08-24T10:15:00+00:00',
  },
]

export const CARD: KnowledgeCard = {
  common_name: 'Tenggiri',
  scientific_name: 'Scomberomorus commerson',
  taxonomy_status: 'VERIFIED_TAXONOMY',
  physical_characteristics: 'Tubuh memanjang, punggung kebiruan.',
  taste: 'gurih',
  texture: 'padat',
  processing_methods: ['Digoreng', 'Dibakar', 'Dikukus'],
  commercial_uses: ['Fillet', 'Steak'],
  similar_or_substitute_species: ['kembung', 'tuna'],
  potential_buyer_segments: ['rumah makan'],
  limitations: ['Identifikasi visual tidak menjamin kesegaran'],
  sources: [
    {
      source_id: 's1',
      title: 'FishBase Tenggiri',
      source_type: 'database',
      url: 'https://example.test/tenggiri',
      publisher: 'FishBase',
      reviewed_at: '2026-08-01T00:00:00Z',
      verification_status: 'verified',
    },
  ],
}

export const REASONS: MatchReason[] = [
  { criterion: 'intended_use', met: true, detail: 'cocok untuk digoreng', value: 'digoreng' },
  { criterion: 'characteristics', met: true, detail: 'ciri sesuai preferensi', value: 'gurih' },
  { criterion: 'price', met: true, detail: 'Rp 68.000/kg', value: '68000' },
  { criterion: 'volume', met: true, detail: '24 kg', value: '24 kg' },
  { criterion: 'distance', met: false, detail: 'di luar radius layanan', value: '120 km' },
]
