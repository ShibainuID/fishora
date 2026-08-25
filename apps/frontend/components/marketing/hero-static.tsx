import { Logo } from '@/components/common/logo'

export function HeroStatic() {
  return (
    // The sticky nav sits in flow above this, so a full-viewport hero pushes
    // its own CTAs below the fold by exactly the nav height (60px, 68px at lg).
    <section
      data-block="hero"
      className="mx-auto flex min-h-[calc(100dvh-60px)] w-full max-w-[1200px] flex-col justify-end gap-4 px-4 pt-16 pb-8 lg:min-h-[calc(100dvh-68px)] lg:px-8"
    >
      <h1 className="hero-rise text-display-2 max-w-[16ch] lg:max-w-[22ch]">
        Discover the value beneath the ocean
      </h1>
      {/* The same lockup the nav carries, one step larger: the headline names
          the promise, the lockup says whose it is, then the description. */}
      <Logo
        className="hero-rise text-[1.375rem] lg:text-[1.5rem]"
        style={{ '--rise-delay': '0.08s' } as React.CSSProperties}
      />
      <p
        className="hero-rise text-body max-w-[36ch]"
        style={{ '--rise-delay': '0.16s' } as React.CSSProperties}
      >
        Fishora identifies each catch, explains its commercial value, and matches it to buyers who can use it.
      </p>
      <div
        className="hero-rise flex flex-col gap-3 lg:flex-row lg:items-center lg:gap-4"
        style={{ '--rise-delay': '0.24s' } as React.CSSProperties}
      >
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
