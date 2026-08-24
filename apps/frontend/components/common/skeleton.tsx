/**
 * Skeleton. DESIGN.md 9.
 *
 * Skeletons are shaped like the content they replace, never a generic grey box
 * and never a centred spinner. The shimmer is a single transform-based sweep,
 * which the reduced-motion backstop in globals.css disables for free.
 */

export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={[
        'relative block overflow-hidden rounded-[var(--radius-input)] bg-bg-sunken',
        'after:absolute after:inset-0 after:-translate-x-full',
        'after:animate-[shimmer_1.6s_infinite]',
        'after:bg-gradient-to-r after:from-transparent after:via-line after:to-transparent',
        className,
      ].join(' ')}
    />
  )
}

/**
 * The LotCard skeleton, shaped to the real card: a 4:3 media block then four
 * text bars at the real widths. DESIGN.md 8.7.
 */
export function SkeletonLotCard() {
  return (
    <div className="flex flex-col gap-3">
      <Skeleton className="aspect-[4/3] w-full rounded-[var(--radius-card)]" />
      <div className="flex flex-col gap-2 px-1">
        <Skeleton className="h-5 w-2/5" />
        <Skeleton className="h-4 w-3/5" />
        <Skeleton className="h-4 w-1/4" />
        <Skeleton className="h-5 w-1/3" />
      </div>
    </div>
  )
}
