import { List } from '@phosphor-icons/react/dist/ssr'
import { Button } from '@/components/common/button'
import { IdentificationDemo } from '@/components/marketing/identification-demo'
import type { PredictionCard } from '@/components/fish/prediction-card'
import { LotCard } from '@/components/lot/lot-card'
import { MatchReasons } from '@/components/lot/match-reasons'
import { FlowPan } from '@/components/marketing/flow-pan'
import { FlowStrip } from '@/components/marketing/flow-strip'
import { HeroDescent } from '@/components/marketing/hero-descent'
import type { components } from '@/lib/api/schema'

type Lot = components['schemas']['LotResponse']

const DEMO_LOT: Lot = {
  id: 'lot_tenggiri_1',
  prediction_id: 'pred_ok',
  operator_id: 'op_rian',
  species_id: 'species_tenggiri',
  landing_point_id: 'lp_muara_angke',
  quantity_kg: '24.000',
  size_category: 'L',
  starting_price_per_kg: '68000.00',
  status: 'active',
  auction_starts_at: '2026-08-24T10:00:00+00:00',
  auction_ends_at: '2026-08-24T14:00:00+00:00',
  public_slug: 'tenggiri-lot1',
  allocated_buyer_id: null,
  current_highest_per_kg: '70000.00',
  serviceability_radius_km: 100,
}

const DEMO_REASONS = [
  { criterion: 'intended_use', met: true, detail: 'cocok untuk digoreng', value: 'digoreng' },
  { criterion: 'characteristics', met: true, detail: 'ciri sesuai preferensi', value: 'gurih' },
  { criterion: 'price', met: true, detail: 'Rp 68.000/kg', value: '68000' },
  { criterion: 'volume', met: true, detail: '24 kg', value: '24 kg' },
  { criterion: 'distance', met: true, detail: '37 km', value: '37 km' },
]

const DEMO_ID: Parameters<typeof PredictionCard>[0]['result'] = {
  prediction_id: 'pred_demo',
  model_version: 'v1',
  status: 'confident_prediction',
  prediction: { species_id: 'species_tenggiri', normalized_label: 'tenggiri', confidence: 0.91 },
  top_candidates: [
    { species_id: 'species_tenggiri', normalized_label: 'tenggiri', confidence: 0.91 },
    { species_id: 'species_kembung', normalized_label: 'kembung', confidence: 0.06 },
  ],
  threshold: 0.8,
  verification_status: 'pending',
}

export function LandingPage() {
  return (
    <div className="bg-abyss-950 text-abyss-50">
      <header className="sticky top-0 flex h-[60px] items-center gap-3 px-4 lg:h-[68px]">
        <p className="text-[1.0625rem] font-semibold tracking-[-0.02em]">
          Fishora<span className="text-accent">.</span>
        </p>
        <nav className="ml-auto hidden items-center gap-6 lg:flex" aria-label="Primary">
          <a className="min-h-11 px-2" href="#platform">Platform</a>
          <a className="min-h-11 px-2" href="#buyers">Buyers</a>
          <a className="min-h-11 px-2" href="#operators">Operators</a>
          <a className="min-h-11 px-2" href="#knowledge">Knowledge</a>
        </nav>
        <a href="#access" className="ml-auto lg:ml-6">
          <Button size="sm" type="button">Request access</Button>
        </a>
        <button type="button" className="grid size-11 place-items-center lg:hidden" aria-label="Open menu">
          <List size={22} />
        </button>
      </header>

      <HeroDescent />

      <section data-block="gap" className="px-4 py-16">
        <p className="text-display-2 max-w-[18ch]">
          Indonesian boats land hundreds of species. Buyers order a handful.
        </p>
        <dl className="mt-12 flex flex-col gap-8 md:flex-row md:gap-16">
          <div className="border-t border-abyss-800 pt-4">
            <dt className="text-num-xl text-accent">100 km</dt>
            <dd className="text-body-sm mt-2">serviceability radius, MVP</dd>
          </div>
          <div className="border-t border-abyss-800 pt-4">
            <dt className="text-num-xl text-accent">5 to 10</dt>
            <dd className="text-body-sm mt-2">species in the MVP model</dd>
          </div>
          <div className="border-t border-abyss-800 pt-4">
            <dt className="text-num-xl text-accent">under 90s</dt>
            <dd className="text-body-sm mt-2">from photo to published lot</dd>
          </div>
        </dl>
      </section>

      <section data-block="flow" className="py-16">
        <p className="text-eyebrow px-4 text-ink-faint">THE FLOW</p>
        <FlowPan>
          <FlowStrip />
        </FlowPan>
      </section>

      <section data-block="identify" id="operators" className="px-4 py-16">
        <h2 className="text-h1">The model proposes. A person decides.</h2>
        <p className="text-body mt-3 max-w-[25ch]">
          Nothing publishes until an operator confirms the species on the landing floor.
        </p>
        <div className="mt-8">
          <IdentificationDemo result={DEMO_ID} />
        </div>
      </section>

      <section data-block="match" id="buyers" className="px-4 py-16">
        <p className="text-eyebrow text-ink-faint">WHY IT MATCHED</p>
        <h2 className="text-h1 mt-2">Need, then supply, then the reason.</h2>
        <div className="mt-8 flex flex-col gap-6">
          <LotCard lot={DEMO_LOT} photoUrl="/globe.svg" matchPercent={0.94} />
          <MatchReasons reasons={DEMO_REASONS} />
        </div>
      </section>

      <section data-block="knowledge" id="knowledge" className="py-16">
        <h2 className="text-h1 px-4">What a shopper can learn from a QR.</h2>
        <div className="-mx-0 mt-8 flex flex-col gap-4 md:grid md:grid-cols-3">
          <article className="aspect-[4/3] bg-abyss-800 px-4 py-6">
            <p className="text-body">Taste: gurih. Texture: padat.</p>
          </article>
          <article className="bg-abyss-850 px-4 py-6">
            <p className="text-body">Digoreng, dibakar, dikukus.</p>
          </article>
          <article className="bg-abyss-800 px-4 py-6">
            <p className="text-body">Fillet. Steak. Rumah makan.</p>
          </article>
          <article className="bg-gradient-to-b from-abyss-900 to-abyss-800 px-4 py-6">
            <p className="text-body">Kembung. Tuna.</p>
          </article>
          <article className="border border-abyss-800 px-4 py-6">
            <p className="text-num-sm">1 verified source</p>
          </article>
        </div>
      </section>

      <section data-block="built" className="relative mt-8 min-h-[44vh] bg-abyss-800 px-4 py-12">
        <div className="absolute inset-0 bg-abyss-950/60" />
        <div className="relative">
          <p className="text-body-sm">Built for the people who move fish after it lands.</p>
          <ul className="mt-6 flex flex-col gap-2">
            {['supermarket', 'seafood retailer', 'restaurant', 'catering', 'hotel', 'processor', 'distributor'].map((row) => (
              <li key={row} className="text-h3">{row}</li>
            ))}
          </ul>
        </div>
      </section>

      <section data-block="close" id="access" className="px-4 py-24">
        <p className="text-display-2 max-w-[18ch]">
          Discover the value beneath the ocean.
        </p>
        <div className="mt-8">
          <Button block size="lg" type="button">Request access</Button>
        </div>
      </section>

      <footer className="flex flex-col gap-8 px-4 py-16 md:flex-row">
        <p className="text-h3">Fishora</p>
        <a className="min-h-11" href="#flow">See the flow</a>
        <p className="text-body-sm">Jakarta</p>
      </footer>
    </div>
  )
}
