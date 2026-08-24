import { SPECIES, isSpeciesLabel } from '@/lib/species'
import { Stratum } from '@/components/marketing/sea-strata'

/**
 * Stands in for catch photography until real photographs exist.
 *
 * Not a stock photo: a random image would put an unrelated scene on a card
 * labelled Tenggiri, which misinforms a buyer deciding what to bid on. Not a
 * drawn fish either, because eleven hand-drawn silhouettes would look worse
 * than nothing. Instead each species gets a deterministic depth composition and
 * its own name, so a grid of lots reads as a designed system and every card is
 * still visually distinct.
 *
 * Deterministic from the label, so the same fish always looks the same.
 *
 * The caller owns the box. className lands on the root, so a caller can pass
 * `absolute inset-0` or `aspect-[4/3] w-full` and either works; the root never
 * sets its own position, because a position utility here would beat the
 * caller's by stylesheet order and silently collapse the box to zero height.
 */
export function SpeciesArt({
  label,
  className = '',
}: {
  label: string
  className?: string
}) {
  const name = isSpeciesLabel(label) ? SPECIES[label].commonName : label
  const tone = toneFor(label)

  return (
    <div
      className={`overflow-hidden bg-abyss-800 ${className}`}
      role="img"
      aria-label={`Ilustrasi ${name}`}
    >
      {/* Containing block for the strata, kept off the root so the caller's
          position utility is free to win. */}
      <div className="relative size-full">
        {/* Depth, angled per species so no two cards share a horizon. */}
        <div
          className="absolute inset-0"
          style={{ transform: `rotate(${tone.tilt}deg) scale(1.25)` }}
        >
          <Stratum depth={0} className="absolute inset-x-0 top-[26%] h-[74%] w-full" />
          <Stratum depth={2} className="absolute inset-x-0 top-[50%] h-[64%] w-full" />
          <Stratum depth={4} className="absolute inset-x-0 top-[74%] h-[50%] w-full" />
        </div>

        {/* One light per species, placed differently each time. */}
        <div
          className="absolute size-24 rounded-full bg-[radial-gradient(circle,var(--color-lamp-400)_0%,transparent_66%)] blur-xl"
          style={{ left: `${tone.lightX}%`, top: `${tone.lightY}%`, opacity: tone.lightOpacity }}
        />

        <p className="text-num-sm absolute bottom-3 left-3 text-abyss-100">{name}</p>
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
    tilt: -8 + (hash % 17),
    lightX: 18 + (hash % 58),
    lightY: 8 + (hash % 26),
    lightOpacity: 0.22 + ((hash % 5) * 0.05),
  }
}
