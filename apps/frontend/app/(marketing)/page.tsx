import { Fish, MagnifyingGlass, Sliders } from '@phosphor-icons/react/dist/ssr'
import { Button } from '@/components/common/button'
import { EmptyState } from '@/components/common/empty-state'
import { Skeleton, SkeletonLotCard } from '@/components/common/skeleton'
import { ThemeToggle } from '@/components/common/theme-toggle'
import { KitFields, KitSheet } from '../kit-client'
import { kilograms, kilometres, percent, rupiahPerKg } from '@/lib/format'

/**
 * Foundations preview. Temporary: this route is replaced by the landing page at
 * build step 8. It exists so the token system and the five primitives can be
 * reviewed at 390x844 in both themes, which the mobile-first mandate in
 * DESIGN.md 1.3 requires before any breakpoint prefix gets written.
 */
export default function Page() {
  return (
    <main className="mx-auto max-w-[1400px] px-4 py-8 md:px-6 lg:px-8">
      <header className="mb-10 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-h1 text-ink">Fishora foundations</h1>
          <p className="text-body-sm mt-1 text-ink-muted">
            Tokens and primitives. Review at 390 wide, in both themes.
          </p>
        </div>
        <ThemeToggle />
      </header>

      <div className="flex flex-col gap-12">
        <Section title="Palette">
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-8">
            {[
              'bg-abyss-950',
              'bg-abyss-800',
              'bg-abyss-600',
              'bg-abyss-400',
              'bg-abyss-200',
              'bg-abyss-100',
              'bg-abyss-50',
              'bg-abyss-25',
            ].map((c) => (
              <div
                key={c}
                className={`${c} h-14 rounded-[var(--radius-input)] border border-line`}
              />
            ))}
          </div>
          <div className="mt-2 grid grid-cols-4 gap-2 sm:grid-cols-8">
            {[
              'bg-lamp-600',
              'bg-lamp-500',
              'bg-lamp-400',
              'bg-lamp-300',
              'bg-lamp-100',
            ].map((c) => (
              <div
                key={c}
                className={`${c} h-14 rounded-[var(--radius-input)] border border-line`}
              />
            ))}
          </div>
          <p className="text-body-sm mt-3 text-ink-muted">
            One accent for the whole product. The lamp is the only warm value in
            the system.
          </p>
        </Section>

        <Section title="Type">
          <p className="text-display-2 text-ink">Discover the value</p>
          <p className="text-h1 mt-3 text-ink">Tenggiri</p>
          <p className="text-body mt-1 max-w-[65ch] text-ink-muted italic">
            Scomberomorus commerson
          </p>
          <p className="text-body mt-4 max-w-[65ch] text-ink">
            Fishora identifies each catch, explains its commercial value, and
            matches it to buyers who can use it.
          </p>
          <p className="text-eyebrow mt-6 text-ink-faint">The flow</p>
        </Section>

        <Section title="Quantities">
          <dl className="flex flex-col gap-2">
            {[
              ['Price', rupiahPerKg(68000)],
              ['Quantity', kilograms(24)],
              ['Distance', kilometres(37.4)],
              ['Confidence', percent(0.91)],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex items-baseline justify-between gap-4 border-b border-line pb-2"
              >
                <dt className="text-body-sm text-ink-muted">{label}</dt>
                <dd className="text-num text-ink">{value}</dd>
              </div>
            ))}
          </dl>
          <p className="text-body-sm mt-3 text-ink-muted">
            Tabular and mono, so figures in a column line up on the decimal.
          </p>
        </Section>

        <Section title="Buttons">
          <div className="flex flex-col gap-3">
            <Button block size="lg">
              Request access
            </Button>
            <Button block size="lg" variant="secondary">
              See the flow
            </Button>
            <div className="flex flex-wrap gap-3">
              <Button>Place bid</Button>
              <Button variant="secondary">Change species</Button>
              <Button variant="ghost">Clear all</Button>
              <Button variant="danger">Withdraw</Button>
              <Button loading>Place bid</Button>
              <Button disabled>Place bid</Button>
              <Button size="sm" variant="secondary" icon={<Sliders className="size-4" />}>
                Filters
              </Button>
            </div>
          </div>
          <p className="text-body-sm mt-3 text-ink-muted">
            Full width at lg on phones for the two landing CTAs. The loading
            button keeps its width.
          </p>
        </Section>

        <Section title="Fields">
          <KitFields />
        </Section>

        <Section title="Sheet">
          <KitSheet />
          <p className="text-body-sm mt-3 text-ink-muted">
            Bottom sheet on phones, centred dialog at md. Escape closes, the
            backdrop closes, the page behind does not scroll.
          </p>
        </Section>

        <Section title="Loading">
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            <SkeletonLotCard />
            <SkeletonLotCard />
          </div>
          <div className="mt-5 flex flex-col gap-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-1/3" />
          </div>
        </Section>

        <Section title="Empty">
          <div className="rounded-[var(--radius-card)] border border-line bg-surface">
            <EmptyState
              icon={Fish}
              message="No active lots within 100 km right now."
              action={
                <Button variant="secondary" icon={<MagnifyingGlass className="size-4" />}>
                  Widen filters
                </Button>
              }
            />
          </div>
        </Section>
      </div>
    </main>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-h3 mb-4 border-b border-line pb-2 text-ink">{title}</h2>
      {children}
    </section>
  )
}
