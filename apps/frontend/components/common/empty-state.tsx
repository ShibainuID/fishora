import type { ComponentType, ReactNode } from 'react'
import type { IconProps } from '@phosphor-icons/react'

/**
 * EmptyState. DESIGN.md 9.
 *
 * Every empty state names the cause and offers exactly one action. No mascot,
 * no custom illustration: one Phosphor duotone glyph at 40px in --ink-faint.
 * "No results" with no way forward is a dead end, not a state.
 */

export interface EmptyStateProps {
  icon: ComponentType<IconProps>
  /** Names the cause, not the absence. "No lots match these filters". */
  message: string
  /** The single way forward. Omitted only where none exists, e.g. bid history. */
  action?: ReactNode
}

export function EmptyState({ icon: Icon, message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-4 px-6 py-14 text-center">
      <Icon size={40} weight="duotone" className="text-ink-faint" aria-hidden />
      <p className="text-body max-w-[34ch] text-ink-muted">{message}</p>
      {action}
    </div>
  )
}
