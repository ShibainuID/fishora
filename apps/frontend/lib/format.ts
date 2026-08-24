// Locale is pinned: an unpinned one formats differently on server and client.

/** Non-breaking space. */
const NBSP = ' '
/** Zero-width, non-breaking. Stops "68.000/kg" breaking at the slash. */
const WORD_JOINER = '⁠'

const decimal = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 })

/** `68000` -> `Rp 68.000`. Built by hand so ICU drift cannot change it. */
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

/** `37.4` -> `37 km`. Never shown to a decimal: it is only a proxy. */
export function kilometres(value: number): string {
  return `${decimal.format(Math.round(value))}${NBSP}km`
}

/** `0.91` -> `91%`. */
export function percent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`
}

export type ConfidenceBand = 'high' | 'medium' | 'low'

export function confidenceBand(fraction: number): ConfidenceBand {
  if (fraction >= 0.85) return 'high'
  if (fraction >= 0.6) return 'medium'
  return 'low'
}

/** `m:ss` under an hour, `Xh Ym` above it. Pure, so it is safe to render on the server. */
export function countdown(msRemaining: number): string {
  const total = Math.max(0, Math.floor(msRemaining / 1000))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60

  if (hours >= 1) return `${hours}h ${minutes}m`
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

/** Applied at the render boundary, so generated copy cannot reintroduce them. */
export function normaliseDashes(text: string): string {
  return text.replace(/[—–]/g, '-')
}
