import { CheckCircle, XCircle } from '@phosphor-icons/react/dist/ssr'
import type { components } from '@/lib/api/schema'

export type MatchReason = components['schemas']['MatchReasonResponse']

export function MatchReasons({ reasons }: { reasons: MatchReason[] }) {
  const ordered = [...reasons].sort((a, b) => Number(b.met) - Number(a.met))
  return (
    <ul className="flex flex-col gap-2">
      {ordered.map((reason) => {
        const Icon = reason.met ? CheckCircle : XCircle
        return (
          <li key={reason.criterion} className="flex items-start gap-2">
            <Icon
              size={20}
              weight={reason.met ? 'fill' : 'regular'}
              className={reason.met ? 'text-verified' : 'text-ink-faint'}
              data-met={reason.met ? 'true' : 'false'}
              aria-hidden
            />
            <div>
              <p className="text-body-sm text-ink">{reason.detail}</p>
              {reason.value && (
                <p className="text-num-sm tabular-nums text-ink-muted">{reason.value}</p>
              )}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
