'use client'

import { useSyncExternalStore } from 'react'
import { countdown } from '@/lib/format'

const WARN_MS = 5 * 60 * 1000

function subscribe(onChange: () => void) {
  const id = setInterval(onChange, 1000)
  return () => clearInterval(id)
}

const clientClock = () => Date.now()
// The server cannot know the viewer's clock, so it renders no figure at all
// rather than one that will be wrong by the time it arrives.
const serverClock = () => null

export interface CountdownProps {
  endsAt: string
  /** Fixes the clock. Supplied by tests; omitted in the app so it ticks live. */
  now?: number
}

export function Countdown({ endsAt, now }: CountdownProps) {
  // useSyncExternalStore is the sanctioned way to read a changing external
  // value: no impure call in render, and no setState inside an effect.
  const live = useSyncExternalStore(subscribe, clientClock, serverClock)
  const clock = now ?? live

  const remaining = clock === null ? null : new Date(endsAt).getTime() - clock
  const warn = remaining !== null && remaining > 0 && remaining < WARN_MS

  return (
    <time
      dateTime={endsAt}
      suppressHydrationWarning
      className={['text-num-sm tabular-nums', warn ? 'text-state-warn' : 'text-ink'].join(' ')}
    >
      {remaining === null ? '' : countdown(remaining)}
    </time>
  )
}
