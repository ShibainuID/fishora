import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { CircleNotch } from '@phosphor-icons/react/dist/ssr'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

const VARIANT: Record<Variant, string> = {
  primary: 'bg-accent text-accent-ink hover:brightness-105',
  secondary:
    'border border-line-strong text-ink hover:bg-bg-sunken hover:border-ink-faint',
  ghost: 'text-ink hover:bg-bg-sunken',
  danger:
    'border border-state-error text-state-error hover:bg-state-error hover:text-white',
}

const SIZE: Record<Size, string> = {
  sm: 'min-h-11 px-4 text-body-sm',
  md: 'h-11 px-5 text-body-sm',
  lg: 'h-13 px-6 text-body',
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  /** Stretches to the container. Default for primary actions on phones. */
  block?: boolean
  icon?: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  block = false,
  icon,
  className = '',
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={[
        'relative inline-flex shrink-0 items-center justify-center gap-2 rounded-full',
        'font-medium whitespace-nowrap',
        'transition-[transform,background-color,border-color,color,filter]',
        'duration-150 ease-[var(--ease-out-quint)]',
        'active:translate-y-px active:scale-[0.98]',
        'disabled:pointer-events-none disabled:opacity-45',
        VARIANT[variant],
        SIZE[size],
        block ? 'w-full' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {/* The label stays in flow while loading, just invisible, so the button
          keeps its exact width and nothing around it reflows. */}
      <span
        className={[
          'inline-flex items-center gap-2',
          loading ? 'invisible' : '',
        ].join(' ')}
      >
        {icon}
        {children}
      </span>
      {loading && (
        <span className="absolute inset-0 grid place-items-center">
          <CircleNotch className="size-4 animate-spin" aria-hidden />
          <span className="sr-only">Loading</span>
        </span>
      )}
    </button>
  )
}
