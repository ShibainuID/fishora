import { countdown } from '@/lib/format'

const WARN_MS = 5 * 60 * 1000

export interface CountdownProps {
  endsAt: string
  now?: number
}

export function Countdown({ endsAt, now }: CountdownProps) {
  const remaining = new Date(endsAt).getTime() - (now ?? Date.now())
  const warn = remaining > 0 && remaining < WARN_MS
  return (
    <time
      dateTime={endsAt}
      className={['text-num-sm tabular-nums', warn ? 'text-state-warn' : 'text-ink'].join(' ')}
    >
      {countdown(remaining)}
    </time>
  )
}
