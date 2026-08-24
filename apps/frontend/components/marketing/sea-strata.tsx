/**
 * The hero's visual, drawn rather than photographed.
 *
 * No footage of a night landing exists yet, and random stock would put an
 * unrelated scene behind a fisheries pitch. So the composition is abstract: five
 * strata of water, and one warm light on the surface. The boat is implied by the
 * light, never illustrated, which keeps this a designed ground rather than an
 * amateur drawing.
 *
 * Vector, so it costs no image bytes, never pixelates, and reads at any
 * viewport. Each stratum is a separate element so the parallax planes can move
 * it independently.
 */

/** One stratum: a wave-edged band of water at a given depth. */
export function Stratum({
  depth,
  className = '',
}: {
  /** 0 is the surface, 4 is the abyss. Drives colour and edge softness. */
  depth: 0 | 1 | 2 | 3 | 4
  className?: string
}) {
  const fill = STRATUM_FILL[depth]
  return (
    <svg
      aria-hidden
      viewBox="0 0 1200 400"
      preserveAspectRatio="none"
      className={className}
      // Vector fills carry the palette, so the strata stay in step with the
      // theme tokens instead of hardcoding a second set of colours.
      style={{ color: fill }}
    >
      <path d={STRATUM_PATH[depth]} fill="currentColor" />
    </svg>
  )
}

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

const STRATUM_FILL: Record<number, string> = {
  0: 'var(--color-abyss-700)',
  1: 'var(--color-abyss-800)',
  2: 'var(--color-abyss-850)',
  3: 'var(--color-abyss-900)',
  4: 'var(--color-abyss-950)',
}

// Hand-tuned so no two edges rhyme: repeated wave shapes read as a pattern
// rather than as water.
const STRATUM_PATH: Record<number, string> = {
  0: 'M0 96 C 180 62, 330 128, 520 104 C 700 82, 860 140, 1040 108 C 1120 94, 1170 104, 1200 98 L1200 400 L0 400 Z',
  1: 'M0 132 C 220 104, 360 168, 560 142 C 760 116, 900 176, 1080 148 C 1140 138, 1176 146, 1200 142 L1200 400 L0 400 Z',
  2: 'M0 186 C 160 158, 380 214, 600 190 C 820 166, 980 220, 1140 196 C 1170 192, 1188 194, 1200 192 L1200 400 L0 400 Z',
  3: 'M0 248 C 240 222, 420 276, 640 254 C 860 232, 1000 282, 1200 258 L1200 400 L0 400 Z',
  4: 'M0 318 C 280 298, 460 342, 700 324 C 940 306, 1060 344, 1200 330 L1200 400 L0 400 Z',
}

/** Marine snow. Particulate drifting up as the camera sinks. */
export function MarineSnow({ className = '' }: { className?: string }) {
  return (
    <div aria-hidden className={className}>
      {SNOW.map((flake, index) => (
        <span
          key={index}
          className="absolute rounded-full bg-abyss-200"
          style={{
            left: `${flake.x}%`,
            top: `${flake.y}%`,
            width: flake.size,
            height: flake.size,
            opacity: flake.opacity,
            animation: `marine-snow ${flake.duration}s linear ${flake.delay}s infinite`,
          }}
        />
      ))}
    </div>
  )
}

// Fixed, not random: Math.random in render would break hydration, and a stable
// set is easier to tune than a generated one.
const SNOW = [
  { x: 8, y: 82, size: 2, opacity: 0.22, duration: 15, delay: 0 },
  { x: 17, y: 64, size: 3, opacity: 0.16, duration: 19, delay: 2.4 },
  { x: 26, y: 91, size: 2, opacity: 0.26, duration: 13, delay: 1.1 },
  { x: 34, y: 73, size: 2, opacity: 0.14, duration: 21, delay: 4.2 },
  { x: 43, y: 88, size: 3, opacity: 0.2, duration: 17, delay: 0.6 },
  { x: 51, y: 68, size: 2, opacity: 0.18, duration: 23, delay: 3.3 },
  { x: 59, y: 84, size: 2, opacity: 0.24, duration: 14, delay: 5.1 },
  { x: 68, y: 76, size: 3, opacity: 0.15, duration: 20, delay: 1.8 },
  { x: 76, y: 93, size: 2, opacity: 0.21, duration: 16, delay: 3.9 },
  { x: 84, y: 70, size: 2, opacity: 0.17, duration: 22, delay: 2.7 },
  { x: 91, y: 86, size: 3, opacity: 0.19, duration: 18, delay: 4.8 },
] as const
