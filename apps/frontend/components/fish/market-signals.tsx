import { ChatCircle } from '@phosphor-icons/react/dist/ssr'
import { EmptyState } from '@/components/common/empty-state'
import { normaliseDashes } from '@/lib/format'
import type { Review } from '@/lib/api/commerce'

// The unverified surface: no shield, no verified edge, unlike KnowledgeCard.
export interface MarketSignalsProps {
  reviews: Review[]
}

export function MarketSignals({ reviews }: MarketSignalsProps) {
  return (
    <section className="rounded-2xl bg-bg-sunken px-5 py-5">
      <h2 className="text-h3 text-ink">Sinyal pasar</h2>
      <p className="text-body-sm mt-1 text-ink-muted">
        Umpan balik pembeli dan konsumen. Bukan pengetahuan terverifikasi.
      </p>
      {reviews.length === 0 ? (
        <EmptyState
          icon={ChatCircle}
          message="Belum ada umpan balik pembeli untuk spesies ini."
        />
      ) : (
        <ul className="mt-4 flex flex-col gap-4">
          {reviews.map((review) => (
            <li key={review.id} className="flex flex-col gap-1">
              <p className="text-label text-ink">{normaliseDashes(review.actual_use)}</p>
              {/* A count, not a track: DESIGN.md 8.5 bans filled progress bars. */}
              <p className="text-body-sm tabular-nums text-ink-muted">
                Kesesuaian olahan {review.processing_suitability} dari 5
              </p>
              {review.substitute_acceptance === true && (
                <p className="text-body-sm text-ink-muted">Bisa dipakai sebagai pengganti</p>
              )}
              {review.comment && (
                <p className="text-body-sm text-ink-muted">{normaliseDashes(review.comment)}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
