import { ChatCircle } from '@phosphor-icons/react/dist/ssr'
import { EmptyState } from '@/components/common/empty-state'
import { normaliseDashes } from '@/lib/format'

/**
 * MarketSignals, the unverified surface. DESIGN.md 8.4.1.
 *
 * Deliberately different from KnowledgeCard: sunken ground, no shield, no
 * 2px verified edge. Buyer reviews live here, keyed by species so a review
 * of Tenggiri from one landing point appears on every Tenggiri lot, not only
 * the fisherman who sold that catch.
 */
export interface MarketSignal {
  businessType: string
  useCase: string
  body?: string
}

export interface MarketSignalsProps {
  signals: MarketSignal[]
}

export function MarketSignals({ signals }: MarketSignalsProps) {
  return (
    <section className="rounded-2xl bg-bg-sunken px-5 py-5">
      <h2 className="text-h3 text-ink">Sinyal pasar</h2>
      <p className="text-body-sm mt-1 text-ink-muted">
        Umpan balik pembeli dan konsumen. Bukan pengetahuan terverifikasi.
      </p>
      {signals.length === 0 ? (
        <EmptyState
          icon={ChatCircle}
          message="Belum ada umpan balik pembeli untuk spesies ini."
        />
      ) : (
        <ul className="mt-4 flex flex-col gap-4">
          {signals.map((signal) => (
            <li key={`${signal.businessType}-${signal.useCase}`} className="flex flex-col gap-1">
              <p className="text-label text-ink">{normaliseDashes(signal.businessType)}</p>
              <p className="text-body-sm text-ink-muted">{normaliseDashes(signal.useCase)}</p>
              {signal.body && (
                <p className="text-body-sm text-ink-muted">{normaliseDashes(signal.body)}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
