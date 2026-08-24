/**
 * Motion tokens. DESIGN.md 3.5.
 * Only `transform`, `opacity` and `filter` animate. Never width, height, top, left.
 */

export const EASE = {
  /** Entrances. */
  out: [0.16, 1, 0.3, 1],
  /** Reversible state changes. */
  inOut: [0.65, 0, 0.35, 1],
} as const

export const DUR = {
  instant: 0.12,
  fast: 0.2,
  base: 0.32,
  slow: 0.55,
  cinematic: 0.9,
} as const

export const SPRING = {
  ui: { type: 'spring', stiffness: 320, damping: 30, mass: 0.6 },
  gentle: { type: 'spring', stiffness: 120, damping: 22 },
} as const

/**
 * The standard scroll reveal. Capped at 6 children by convention: a stagger
 * longer than that stops reading as one gesture and starts reading as a queue.
 */
export const reveal = (index = 0) =>
  ({
    initial: { opacity: 0, y: 24 },
    whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, amount: 0.3 },
    transition: { duration: 0.6, delay: index * 0.06, ease: EASE.out },
  }) as const
