import type { ComponentType, ReactNode } from 'react'
import type { IconProps } from '@phosphor-icons/react'

export interface EmptyStateProps {
  icon: ComponentType<IconProps>
  /** Names the cause, not the absence. */
  message: string
  /** Omitted only where no action exists. */
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
