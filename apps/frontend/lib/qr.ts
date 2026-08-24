export function discoverUrl(
  slug: string,
  origin = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3111'
) {
  return `${origin}/discover/${slug}`
}

export function qrPayload(slug: string) {
  return discoverUrl(slug)
}

/** Where the second code on the printed card points. No store URL: there is no
 *  published app listing, so this resolves to the site. */
export function appUrl(
  origin = process.env.NEXT_PUBLIC_APP_URL ?? process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3111'
) {
  return origin
}

/** `app` is not a lot id, so the route reserves it as a payload keyword. */
export const APP_QR_KEYWORD = 'app'

export const QR_EXPORTS = [
  { id: 'display', label: 'Display card', mm: '105x148' },
  { id: 'label', label: 'Package label', mm: '40x40' },
  { id: 'menu', label: 'Menu insert', mm: '60x60' },
] as const
