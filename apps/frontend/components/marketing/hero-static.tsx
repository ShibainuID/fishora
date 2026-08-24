export function HeroStatic() {
  return (
    // The sticky nav sits in flow above this, so a full-viewport hero pushes
    // its own CTAs below the fold by exactly the nav height (60px, 68px at lg).
    <section
      data-block="hero"
      className="flex min-h-[calc(100dvh-60px)] flex-col justify-end gap-4 px-4 pt-16 pb-8 lg:min-h-[calc(100dvh-68px)]"
    >
      <h1 className="text-display-2 max-w-[16ch] lg:max-w-[22ch]">Discover the value beneath the ocean</h1>
      <p className="text-body max-w-[36ch]">
        Fishora identifies each catch, explains its commercial value, and matches it to buyers who can use it.
      </p>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:gap-4">
        <ButtonLink href="#access">Request access</ButtonLink>
        <ButtonLink href="#flow" secondary>
          See the flow
        </ButtonLink>
      </div>
    </section>
  )
}

function ButtonLink({
  href,
  children,
  secondary,
}: {
  href: string
  children: string
  secondary?: boolean
}) {
  return (
    <a
      href={href}
      className={[
        'inline-flex min-h-11 items-center justify-center rounded-full px-6 text-body-sm font-medium',
        'lg:w-auto',
        secondary
          ? 'border border-line-strong text-ink'
          : 'bg-accent text-accent-ink',
      ].join(' ')}
    >
      {children}
    </a>
  )
}
