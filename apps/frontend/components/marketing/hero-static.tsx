export function HeroStatic() {
  return (
    <section
      data-block="hero"
      className="flex min-h-dvh flex-col justify-end gap-4 px-4 pt-16 pb-8"
    >
      <h1 className="text-display-2 max-w-[12ch]">Discover the value beneath the ocean</h1>
      <p className="text-body max-w-[36ch]">
        Fishora identifies each catch, explains its commercial value, and matches it to buyers who can use it.
      </p>
      <div className="flex flex-col gap-3">
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
        'inline-flex min-h-11 items-center justify-center rounded-full px-5 text-body-sm font-medium',
        secondary
          ? 'border border-line-strong text-ink'
          : 'bg-accent text-accent-ink',
      ].join(' ')}
    >
      {children}
    </a>
  )
}
