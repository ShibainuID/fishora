/**
 * Number and unit formatting. DESIGN.md 2.3.
 *
 * The locale is pinned to `id-ID` rather than left to the runtime. That is not
 * only a product decision: an unpinned `toLocaleString()` formats with the
 * server's locale during SSR and the browser's on hydration, which is a
 * guaranteed mismatch. Pinning makes both sides agree by construction.
 *
 * Every value these return is rendered in mono with tabular numerals.
 */

/** Non-breaking space. Welds "Rp" to its figure and "24" to its unit. */
const NBSP = ' '
/** Zero-width and non-breaking. Stops "68.000/kg" breaking at the slash. */
const WORD_JOINER = '⁠'

const decimal = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 })

/** `68000` -> `Rp 68.000`. Built by hand so ICU version drift cannot change it. */
export function rupiah(value: number): string {
  return `Rp${NBSP}${decimal.format(Math.round(value))}`
}

/** `68000` -> `Rp 68.000/kg`, unbreakable. */
export function rupiahPerKg(value: number): string {
  return `${rupiah(value)}${WORD_JOINER}/kg`
}

/** `24` -> `24 kg`. */
export function kilograms(value: number): string {
  return `${decimal.format(value)}${NBSP}kg`
}

/** `37.4` -> `37 km`. Distance is never shown to a decimal: it is a proxy. */
export function kilometres(value: number): string {
  return `${decimal.format(Math.round(value))}${NBSP}km`
}

/** `0.91` -> `91%`. */
export function percent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`
}

/**
 * Confidence never renders as a bare number. DESIGN.md 8.5: a numeral plus a
 * one-word verdict, because colour alone is not allowed to carry meaning.
 */
export type ConfidenceBand = 'high' | 'medium' | 'low'

export function confidenceBand(fraction: number): ConfidenceBand {
  if (fraction >= 0.85) return 'high'
  if (fraction >= 0.6) return 'medium'
  return 'low'
}

/**
 * `H:MM:SS` under an hour, `Xh Ym` above it. DESIGN.md 8.9.
 * Takes remaining milliseconds so the caller owns the clock and the drift
 * correction; this stays pure and therefore safe to render on the server.
 */
export function countdown(msRemaining: number): string {
  const total = Math.max(0, Math.floor(msRemaining / 1000))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60

  if (hours >= 1) return `${hours}h ${minutes}m`
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

/**
 * Long dashes are banned in every visible string, including generated copy
 * coming back from the RAG service. DESIGN.md 2.2. Applied at the render
 * boundary so no upstream fix is needed for the ban to hold.
 */
export function normaliseDashes(text: string): string {
  return text.replace(/[—–]/g, '-')
}
