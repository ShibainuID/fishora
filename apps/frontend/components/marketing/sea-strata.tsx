/**
 * What sits over the hero photograph: one warm light on the surface.
 *
 * The water used to be drawn here as five vector strata, and particulate used
 * to drift up through them, because no footage existed. The water is a real
 * photograph now and the drifting specks read as dust on the lens over it, so
 * only the light remains.
 *
 * The boat is implied by the light, never illustrated.
 */

/**
 * The deck lamp: the only warm value in the composition.
 *
 * Small and intense with fast falloff. A wide soft wash reads as sunrise and
 * turns the hero into a gradient blob; a lamp at night is a point of light.
 * Sits right of centre so the copy column stays clear.
 */
export function LampGlow({ className = '' }: { className?: string }) {
  return (
    <div aria-hidden className={className}>
      {/* Outer falloff. Wide but faint, so it suggests haze without washing out. */}
      <div className="absolute top-[6%] left-[52%] size-[26rem] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,var(--color-lamp-500)_0%,transparent_58%)] opacity-[0.16] blur-2xl lg:left-[62%]" />
      {/* Core. Tight and bright: this is the light itself. */}
      <div className="absolute top-[13%] left-[52%] size-[7rem] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,var(--color-lamp-100)_0%,var(--color-lamp-400)_34%,transparent_70%)] opacity-80 blur-md lg:left-[62%]" />
      {/* Reflection: a lamp over water throws a vertical smear, not a disc. */}
      <div className="absolute top-[20%] bottom-0 left-[52%] w-[3.5rem] -translate-x-1/2 bg-[linear-gradient(to_bottom,var(--color-lamp-400),transparent_72%)] opacity-[0.22] blur-lg lg:left-[62%]" />
    </div>
  )
}

