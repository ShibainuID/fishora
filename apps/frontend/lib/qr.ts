export function discoverUrl(
  slug: string,
  origin = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3111'
) {
  return `${origin}/discover/${slug}`
}

export function qrPayload(slug: string) {
  return discoverUrl(slug)
}

export const QR_EXPORTS = [
  { id: 'display', label: 'Display card', mm: '105x148' },
  { id: 'label', label: 'Package label', mm: '40x40' },
  { id: 'menu', label: 'Menu insert', mm: '60x60' },
] as const
