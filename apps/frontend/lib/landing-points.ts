/** The MVP landing points. Mock data until the backend seeds a real list. */
export const LANDING_POINTS = ['PPI Muara Angke', 'TPI Cilacap', 'PPI Karangsong'] as const

export type LandingPointName = (typeof LANDING_POINTS)[number]

export const LANDING_POINT_IDS: Record<LandingPointName, string> = {
  'PPI Muara Angke': 'lp_muara_angke',
  'TPI Cilacap': 'lp_cilacap',
  'PPI Karangsong': 'lp_karangsong',
}

const NAME_BY_ID: Record<string, string> = Object.fromEntries(
  Object.entries(LANDING_POINT_IDS).map(([name, id]) => [id, name])
)

/**
 * A readable name for a landing point id.
 *
 * Falls back to the id rather than an empty string: a printed card showing
 * `lp_muara_angke` is poor, but one showing nothing where the origin should be
 * is worse.
 */
export function landingPointName(id: string): string {
  return NAME_BY_ID[id] ?? id
}
