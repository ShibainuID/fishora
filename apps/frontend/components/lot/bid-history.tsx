import { dateTime, rupiahPerKg } from '@/lib/format'
import type { components } from '@/lib/api/schema'

type Bid = components['schemas']['BidResponse']

/**
 * The endpoint returns amounts, timestamps and buyer ids and nothing else, so
 * the id is shown verbatim: a display name here would be invented, not fetched.
 * Heading-free, so the caller can title it or let a Sheet header do that.
 */
export function BidHistory({ bids }: { bids: Bid[] }) {
  const ordered = [...bids].sort((a, b) => b.created_at.localeCompare(a.created_at))

  return (
    <>
      {ordered.length === 0 ? (
        <p className="text-body-sm text-ink-muted">Belum ada penawaran pada lot ini.</p>
      ) : (
        <ol className="flex flex-col divide-y divide-line">
          {ordered.map((bid) => (
            <li key={bid.id} className="flex items-baseline justify-between gap-3 py-2">
              <div className="min-w-0">
                <p className="text-num-sm tabular-nums text-ink">
                  {rupiahPerKg(Number(bid.amount_per_kg))}
                </p>
                <p className="truncate text-body-sm text-ink-muted">
                  Penawar <span className="text-num-sm">{bid.buyer_id}</span>
                </p>
              </div>
              <p className="shrink-0 text-num-sm tabular-nums text-ink-muted">
                {dateTime(bid.created_at)}
              </p>
            </li>
          ))}
        </ol>
      )}
    </>
  )
}
