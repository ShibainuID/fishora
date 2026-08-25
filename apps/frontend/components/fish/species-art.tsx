import Image from 'next/image'
import { SPECIES, isSpeciesLabel } from '@/lib/species'

/**
 * Stands in for catch photography until real photographs exist.
 *
 * Not a stock photo of a fish: a random fish image on a card labelled Tenggiri
 * misinforms a buyer deciding what to bid on. This is open water instead, which
 * is ambient rather than a claim about the species, and the name is always
 * printed over it.
 *
 * The crop and the light are derived from the label, so the same species always
 * looks the same and no two of the eleven land on the same frame. That is what
 * keeps a grid of lots reading as distinct cards rather than one image
 * repeated.
 *
 * The caller owns the box. className lands on the root, so a caller can pass
 * `absolute inset-0` or `aspect-[4/3] w-full` and either works; the root never
 * sets its own position, because a position utility here would beat the
 * caller's by stylesheet order and silently collapse the box to zero height.
 */
export function SpeciesArt({
  label,
  className = '',
  sizes = '(max-width: 640px) 100vw, 33vw',
}: {
  label: string
  className?: string
  sizes?: string
}) {
  const name = isSpeciesLabel(label) ? SPECIES[label].commonName : label
  const tone = toneFor(label)

  return (
    <div
      className={`overflow-hidden bg-abyss-900 ${className}`}
      role="img"
      aria-label={`Ilustrasi ${name}`}
    >
      {/* Containing block for the layers, kept off the root so the caller's
          position utility is free to win. */}
      <div className="relative size-full">
        <Image
          src="/sea.jpg"
          alt=""
          fill
          sizes={sizes}
          className="object-cover"
          style={{ objectPosition: `${tone.cropX}% ${tone.cropY}%` }}
        />

        {/* One light per species, placed differently each time. */}
        <div
          className="absolute size-24 rounded-full bg-[radial-gradient(circle,var(--color-lamp-400)_0%,transparent_66%)] blur-xl"
          style={{ left: `${tone.lightX}%`, top: `${tone.lightY}%`, opacity: tone.lightOpacity }}
        />

        {/* The name sits over a photograph whose brightness varies with the
            crop, so it gets its own scrim rather than trusting the image to be
            dark enough everywhere. */}
        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-abyss-950 to-transparent" />

        <p className="text-num-sm absolute bottom-3 left-3 text-abyss-50">{name}</p>
      </div>
    </div>
  )
}

/**
 * A stable hash of the label, so the composition is fixed per species and no
 * two of the eleven land on the same arrangement.
 */
function toneFor(label: string) {
  let hash = 0
  for (let i = 0; i < label.length; i++) {
    hash = (hash * 31 + label.charCodeAt(i)) % 9973
  }
  return {
    cropX: 10 + (hash % 80),
    cropY: 15 + (hash % 70),
    lightX: 18 + (hash % 58),
    lightY: 8 + (hash % 26),
    lightOpacity: 0.16 + ((hash % 5) * 0.04),
  }
}
