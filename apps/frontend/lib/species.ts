/**
 * The labels the app will show.
 *
 * Narrowed to the species we hold catch photography for. A lot with no
 * photograph of its own species falls back to ambient water, which tells a
 * buyer nothing about what they are bidding on, so the rest stay out of the
 * pickers and filters until their photographs exist. This is the "5 to 10
 * species in the MVP model" the landing page states.
 *
 * The model and the taxonomy still carry more than these. Anything outside this
 * set is handled as an unknown label rather than crashing: see resolveSpecies.
 */
export const SUPPORTED_LABELS = [
  'gembolo',
  'kembung',
  'nila',
  'tenggiri',
  'tuna',
] as const

export type SpeciesLabel = (typeof SUPPORTED_LABELS)[number]

export interface SpeciesNames {
  commonName: string
  scientificName: string | null
  /** Catch photography for this species, served from /public. */
  photo: string
}

// Follows the taxonomy seed: gembolo has no scientific name, tuna is genus-level.
export const SPECIES: Record<SpeciesLabel, SpeciesNames> = {
  gembolo: { commonName: 'Gembolo', scientificName: null, photo: '/gembolo.jpeg' },
  kembung: {
    commonName: 'Kembung',
    scientificName: 'Rastrelliger kanagurta',
    photo: '/kembung.jpg',
  },
  nila: { commonName: 'Nila', scientificName: 'Oreochromis niloticus', photo: '/nila.jpg' },
  tenggiri: {
    commonName: 'Tenggiri',
    scientificName: 'Scomberomorus commerson',
    photo: '/tenggiri.jpeg',
  },
  tuna: { commonName: 'Tuna', scientificName: 'Thunnus spp.', photo: '/tuna.jpeg' },
}

export function resolveSpecies(label: string): SpeciesNames {
  if (isSpeciesLabel(label)) return SPECIES[label]
  // Open water, not a fish: showing some other species' photograph next to an
  // unrecognised label would misinform a buyer about what is in the lot.
  return { commonName: label, scientificName: null, photo: '/sea.jpg' }
}

export function isSpeciesLabel(label: string): label is SpeciesLabel {
  return (SUPPORTED_LABELS as readonly string[]).includes(label)
}
