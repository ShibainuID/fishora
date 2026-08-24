/** The 11 labels the CV model emits. Nothing outside this set is identifiable. */
export const SUPPORTED_LABELS = [
  'bandeng',
  'gelama_bunga',
  'gembolo',
  'gulamah',
  'kembung',
  'kuniran',
  'mujair',
  'nila',
  'senangin',
  'tenggiri',
  'tuna',
] as const

export type SpeciesLabel = (typeof SUPPORTED_LABELS)[number]

export interface SpeciesNames {
  commonName: string
  scientificName: string | null
}

// Follows the taxonomy seed: gembolo has no scientific name, tuna is genus-level.
export const SPECIES: Record<SpeciesLabel, SpeciesNames> = {
  bandeng: { commonName: 'Bandeng', scientificName: 'Chanos chanos' },
  gelama_bunga: { commonName: 'Gelama Bunga', scientificName: 'Pennahia anea' },
  gembolo: { commonName: 'Gembolo', scientificName: null },
  gulamah: { commonName: 'Gulamah', scientificName: 'Johnius belangerii' },
  kembung: { commonName: 'Kembung', scientificName: 'Rastrelliger kanagurta' },
  kuniran: { commonName: 'Kuniran', scientificName: 'Upeneus sulphureus' },
  mujair: { commonName: 'Mujair', scientificName: 'Oreochromis mossambicus' },
  nila: { commonName: 'Nila', scientificName: 'Oreochromis niloticus' },
  senangin: { commonName: 'Senangin', scientificName: 'Eleutheronema tetradactylum' },
  tenggiri: { commonName: 'Tenggiri', scientificName: 'Scomberomorus commerson' },
  tuna: { commonName: 'Tuna', scientificName: 'Thunnus spp.' },
}

export function resolveSpecies(label: string): SpeciesNames {
  if (isSpeciesLabel(label)) return SPECIES[label]
  return { commonName: label, scientificName: null }
}

export function isSpeciesLabel(label: string): label is SpeciesLabel {
  return (SUPPORTED_LABELS as readonly string[]).includes(label)
}
