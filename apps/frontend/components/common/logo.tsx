/**
 * The Fishora wordmark.
 *
 * The mark is a monochrome brush silhouette, rendered as a CSS mask over
 * `bg-current` rather than as an `<img>`. An image would keep its own dark
 * charcoal and disappear against the dark landing; a mask takes the text
 * colour, so one code path works on every surface and in both themes.
 */
export function Logo({
  className = '',
  showWordmark = true,
  style,
}: {
  className?: string
  /** The mark alone, for surfaces too tight for the word. */
  showWordmark?: boolean
  style?: React.CSSProperties
}) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`} style={style}>
      <span
        aria-hidden
        // Sized in em, so the mark keeps its proportion to the wordmark at
        // every place the lockup is set: the nav, the footer, and the hero.
        className="size-[1.65em] shrink-0 bg-current"
        style={{
          maskImage: 'url(/Logo.png)',
          WebkitMaskImage: 'url(/Logo.png)',
          maskSize: 'contain',
          WebkitMaskSize: 'contain',
          maskRepeat: 'no-repeat',
          WebkitMaskRepeat: 'no-repeat',
          maskPosition: 'center',
          WebkitMaskPosition: 'center',
        }}
      />
      {showWordmark && (
        <span className="font-semibold tracking-[-0.02em]">
          Fishora<span className="text-accent">.</span>
        </span>
      )}
      {!showWordmark && <span className="sr-only">Fishora</span>}
    </span>
  )
}
